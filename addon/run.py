"""Add-on entry point: turns the add-on options into arguments for screenshot.py,
renders once and exits. Home Assistant decides when to run it (automation)."""

import json
import logging
import os
import sys
from urllib.parse import urlsplit

OPTIONS_FILE = "/data/options.json"
OUTPUT_DIR = "/media/screenshots"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout
)
log = logging.getLogger("run")

with open(OPTIONS_FILE) as f:
    opts = json.load(f)

# The token is part of cdp_url, so only the host may reach the log.
shown = dict(opts)
if opts.get("cdp_url"):
    shown["cdp_url"] = f"{urlsplit(opts['cdp_url']).hostname} (rest hidden)"
log.info("Options received: %s", json.dumps(shown, ensure_ascii=False))

opts["selectors"] = [s for s in opts.get("selectors", []) if s.strip()]
missing = [o for o in ("cdp_url", "url", "selectors") if not opts.get(o)]
if missing:
    log.error(
        "Empty in %s: %s. Set them in the Configuration tab, press Save and start the add-on again.",
        OPTIONS_FILE,
        ", ".join(missing),
    )
    sys.exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

args = [
    sys.executable, "/app/screenshot.py",
    opts["url"], *opts["selectors"],
    "--output", os.path.join(OUTPUT_DIR, opts["output"]),
    "--width", str(opts["width"]),
    "--height", str(opts["height"]),
    "--gap", str(opts["gap"]),
    "--margin", str(opts["margin"]),
    "--cdp", opts["cdp_url"],
]
for selector in opts.get("hide", []):
    args += ["--hide", selector]
for rule in opts.get("style", []):
    args += ["--style", rule["selector"], rule["css"]]

os.execv(sys.executable, args)  # replace this process with screenshot.py
