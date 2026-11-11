# /// script
# dependencies = ["playwright"]
# ///

import argparse
import logging
import os
import subprocess
import sys
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(
    description="Screenshot one or more elements of a page, each into its own PNG."
)
parser.add_argument("url")
parser.add_argument(
    "--shot",
    action="append",
    required=True,
    nargs=2,
    metavar=("SELECTOR", "OUTPUT"),
    help="element to capture and its output PNG file (repeatable)",
)
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
parser.add_argument(
    "--transparent",
    action="store_true",
    help="leave areas without a background transparent instead of white "
    "(the page's own backgrounds stay, remove them with --style)",
)
parser.add_argument("--width", type=int, default=720, help="viewport width")
parser.add_argument("--height", type=int, default=720, help="viewport height")
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


def save_element(page, selector, output):
    el = page.locator(selector).first  # pierces open shadow DOM
    el.wait_for(state="visible")
    # Write to a temporary file first and rename it, so a reader (e.g. Home Assistant)
    # never sees a half-written image.
    tmp = output + ".tmp"
    el.screenshot(path=tmp, type="png", omit_background=args.transparent)
    os.replace(tmp, output)
    box = el.bounding_box()
    log.info(
        "Saved %s (%dx%d px, %d KB)",
        output,
        box["width"],
        box["height"],
        os.path.getsize(output) // 1024,
    )


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
    # Playwright hides scrollbars only in browsers it launches itself. Without this,
    # a remote browser lays the page out about 15 px narrower.
    context.new_cdp_session(page).send("Emulation.setScrollbarsHidden", {"hidden": True})
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

    # All elements come from this one page load, so a run costs a single browser session.
    log.info("Capturing %d element(s)", len(args.shot))
    for selector, output in args.shot:
        save_element(page, selector, output)
    context.close()
    browser.close()

log.info("Done: %d file(s) in %.1f s", len(args.shot), time.monotonic() - started)
