"""F1 榜单采集的纯逻辑部分(去重、校验)。浏览器抓取在 scrape_board 中实现。"""

def dedupe_keep_order(items):
    """按出现顺序去重,只删完全重复的非空条目,不删任何不同条目。"""
    seen, out = set(), []
    for s in items:
        s = (s or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out

def check_board(board, floor=20):
    """F1 校验:有 error 或条目数低于下限,判该榜失败。"""
    if "error" in board:
        return False
    return board.get("count", 0) >= floor


def scrape_board(page, base, path, scroll_rounds=6):
    """F1:用已打开的 Playwright page 抓一个榜单,返回 (去重列表, 原始链接数)。"""
    page.goto(base + path, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for _ in range(scroll_rounds):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
    raw = page.eval_on_selector_all(
        'a[href^="/repositories/"]',
        "els => els.map(a => (a.innerText||'').trim().replace(/\\s+/g,' '))")
    return dedupe_keep_order(raw), len(raw)
