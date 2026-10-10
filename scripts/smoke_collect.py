import sys, json, yaml, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from playwright.sync_api import sync_playwright
from trendshift_daily.collect import scrape_board, check_board
cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "config", "trendshift.yaml")))
src = cfg["source"]
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); page = b.new_page()
    for name, path in src["boards"].items():
        items, raw_n = scrape_board(page, src["base"], path, src["scroll_rounds"])
        out[name] = {"count": len(items), "raw_links": raw_n, "pass": check_board({"count": len(items)}, src["board_min_items"])}
        print(name, out[name])
    b.close()
print(json.dumps(out, ensure_ascii=False))
