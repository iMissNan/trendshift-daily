from trendshift_daily.collect import dedupe_keep_order, check_board

def test_dedupe_keeps_order_and_drops_only_exact_duplicates():
    raw = ["a/x 1", "b/y 2", "a/x 1", "c/z 3"]
    assert dedupe_keep_order(raw) == ["a/x 1", "b/y 2", "c/z 3"]

def test_dedupe_ignores_blank_and_whitespace_only():
    assert dedupe_keep_order(["", "  ", "a/x 1"]) == ["a/x 1"]

def test_check_board_fails_below_floor():
    assert check_board({"count": 5}, floor=20) is False

def test_check_board_passes_at_floor():
    assert check_board({"count": 20}, floor=20) is True

def test_check_board_fails_on_error_field():
    assert check_board({"error": "timeout"}, floor=20) is False
