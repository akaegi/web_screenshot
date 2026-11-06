"""Add-on entry point: turns the add-on options into arguments for screenshot.py,
renders once and exits. Home Assistant decides when to run it (automation)."""

import json
import os
import sys

OPTIONS_FILE = "/data/options.json"
OUTPUT_DIR = "/media/screenshots"

with open(OPTIONS_FILE) as f:
    opts = json.load(f)

for option in ("cdp_url", "url", "selectors"):
    if not opts.get(option):
        sys.exit(f"{option} is not set - add it in the add-on configuration")

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
