# /// script
# dependencies = ["playwright", "pillow"]
# ///

import argparse
import io
import logging
import os
import subprocess
import sys
import time
from urllib.parse import urlsplit

from PIL import Image
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(
    description="Screenshot one or more elements of a page and stack them vertically."
)
parser.add_argument("url")
parser.add_argument("selectors", nargs="+", help="elements to capture, top to bottom")
parser.add_argument("--output", required=True, help="output PNG file")
parser.add_argument(
    "--hide",
    action="append",
    default=[],
    metavar="SELECTOR",
    help="element to hide with display:none (repeatable)",
)
parser.add_argument(
    "--style",
    action="append",
    default=[],
    nargs=2,
    metavar=("SELECTOR", "CSS"),
    help='set inline styles on matching elements, e.g. --style ".x" "overflow: hidden" '
    "(repeatable)",
)
parser.add_argument("--width", type=int, default=720, help="viewport width")
parser.add_argument("--height", type=int, default=720, help="viewport height")
parser.add_argument("--gap", type=int, default=10, help="spacing between elements in px")
parser.add_argument("--margin", type=int, default=10, help="outer margin in px")
parser.add_argument("--timezone", default="Europe/Zurich", help="browser time zone")
parser.add_argument("--locale", default="de-CH", help="browser locale")
parser.add_argument(
    "--cdp",
    help="CDP URL of a remote browser; without it a local Chromium is used",
)
args = parser.parse_args()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout
)
log = logging.getLogger("screenshot")
started = time.monotonic()

if not args.cdp:
    # Local mode: make sure the Chromium build matching this Playwright
    # version is present (quick no-op when it is already installed).
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def element_image(page, selector):
    el = page.locator(selector).first  # pierces open shadow DOM
    el.wait_for(state="visible")
    return Image.open(io.BytesIO(el.screenshot())).convert("RGB")


with sync_playwright() as p:
    if args.cdp:
        host = urlsplit(args.cdp).hostname
        log.info("Connecting to %s", host)
        try:
            browser = p.chromium.connect_over_cdp(args.cdp)
        except Exception as e:
            # The URL can contain a token, keep it out of the log.
            log.error("Could not connect to %s: %s", host, str(e).replace(args.cdp, "<cdp_url>"))
            sys.exit(1)
    else:
        log.info("Starting local Chromium")
        browser = p.chromium.launch()
    context = browser.new_context(
        viewport={"width": args.width, "height": args.height},
        device_scale_factor=1,
        timezone_id=args.timezone,
        locale=args.locale,
    )
    page = context.new_page()
    log.info("Loading %s", args.url)
    page.goto(args.url, wait_until="networkidle")

    for selector in args.hide:
        page.locator(selector).evaluate_all(
            "els => els.forEach(el => el.style.setProperty('display', 'none', 'important'))"
        )

    for selector, css in args.style:
        page.locator(selector).evaluate_all(
            """(els, css) => {
                for (const decl of css.split(';')) {
                    const i = decl.indexOf(':');
                    if (i < 0) continue;
                    const prop = decl.slice(0, i).trim();
                    const value = decl.slice(i + 1).trim();
                    els.forEach(el => el.style.setProperty(prop, value, 'important'));
                }
            }""",
            css,
        )

    log.info("Capturing %d element(s)", len(args.selectors))
    images = [element_image(page, s) for s in args.selectors]
    context.close()
    browser.close()

m = args.margin
content_width = max(img.width for img in images)
content_height = sum(img.height for img in images) + args.gap * (len(images) - 1)
background = images[0].getpixel((0, 0))

canvas = Image.new("RGB", (content_width + 2 * m, content_height + 2 * m), background)
y = m
for img in images:
    x = m + (content_width - img.width) // 2
    canvas.paste(img, (x, y))
    y += img.height + args.gap

# Write to a temporary file first and rename it, so a reader (e.g. Home Assistant)
# never sees a half-written image.
tmp = args.output + ".tmp"
canvas.save(tmp, format="PNG")
os.replace(tmp, args.output)
log.info(
    "Saved %s (%dx%d px, %d KB) in %.1f s",
    args.output,
    canvas.width,
    canvas.height,
    os.path.getsize(args.output) // 1024,
    time.monotonic() - started,
)