"""Score a finished run against the expected labels in the CSV."""
from policies import ESCALATE_FAMILY


def score(expected: dict, values: dict) -> dict:
    action = (values.get("proposal") or {}).get("action")
    exp_action = expected["expected_action"]
    return {
        "category_ok": values.get("category") == expected["expected_category"],
        "priority_ok": values.get("priority") == expected["expected_priority"],
        "action_ok": action == exp_action or (action in ESCALATE_FAMILY and exp_action in ESCALATE_FAMILY),
        "approval_ok": bool(values.get("needs_approval")) == (expected["needs_approval"] == "Y"),
    }


def summarize(rows: list) -> dict:
    n = len(rows) or 1
    return {k: round(100 * sum(r[k] for r in rows) / n, 1) for k in ("category_ok", "priority_ok", "action_ok", "approval_ok")}
