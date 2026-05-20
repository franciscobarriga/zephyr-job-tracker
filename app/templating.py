"""
Shared Jinja2Templates instance.

Every route module imports `templates` from here so they all share one
config — including `asset_v`, a cache-busting version string appended to
static asset URLs (e.g. /static/main.css?v=<asset_v>). It changes on every
process start, so a fresh deploy always serves fresh CSS to browsers.
"""

import time
from pathlib import Path
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.globals["asset_v"] = str(int(time.time()))
