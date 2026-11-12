"""Plain-Python tool logic (no LLM libraries). tools.py wraps these for the agents."""
import re
from datetime import date

from config import KB_DIR, REFUND_CAP, REFUND_WINDOW_DAYS, TODAY
from data import BILLING, DEVICES, SERVICE_STATUS, USERS
from policies import ACCESS_POLICY


def lookup_user(employee_id: str) -> dict:
    u = USERS.get(str(employee_id).strip())
    if not u:
        return {"found": False, "error": f"No user with id {employee_id}"}
    mgr = USERS.get(u.get("manager_id") or "")
    out = {"found": True, **u}
    out["manager_name"] = mgr["name"] if mgr else None
    return out


def check_access_policy(topic: str) -> dict:
    p = ACCESS_POLICY.get(topic)
    if not p:
        return {"error": f"Unknown topic '{topic}'", "topics": sorted(ACCESS_POLICY)}
    return {"topic": topic, **p}


def check_manager_approval(requester_id: str) -> dict:
    u = USERS.get(str(requester_id).strip())
    if not u:
        return {"found": False}
    mgr = USERS.get(u.get("manager_id") or "")
    return {"found": True, "requester": u["name"],
            "manager": mgr["name"] if mgr else None,
            "manager_id": mgr["id"] if mgr else None,
            "approval_on_file": False,
            "note": "No approval is stored in advance. It is collected at the approval step."}


def get_invoice(invoice_number: str) -> dict:
    inv = BILLING["invoices"].get(str(invoice_number).strip().lstrip("#"))
    return {"found": True, **inv} if inv else {"found": False, "error": f"No invoice {invoice_number}"}


def get_payment_history(customer_id: str) -> dict:
    cid = str(customer_id).strip()
    return {"customer_id": cid,
            "payments": [p for p in BILLING["payments"] if p["customer_id"] == cid],
            "subscriptions": [s for s in BILLING["subscriptions"] if s["customer_id"] == cid],
            "invoices": [i for i in BILLING["invoices"].values() if i["customer_id"] == cid]}


def check_refund_policy(amount: float, purchase_date: str) -> dict:
    try:
        d = date.fromisoformat(purchase_date)
    except ValueError:
        return {"error": "purchase_date must be YYYY-MM-DD"}
    days = (TODAY - d).days
    within_window = days <= REFUND_WINDOW_DAYS
    if not within_window:
        ruling = "denied_outside_window"
    elif amount > REFUND_CAP:
        ruling = "needs_finance_manager"
    else:
        ruling = "allowed_with_approval"
    return {"days_since_purchase": days, "window_days": REFUND_WINDOW_DAYS, "cap": REFUND_CAP,
            "within_window": within_window, "ruling": ruling}


def _read_kb():
    arts = []
    for f in sorted(KB_DIR.glob("KB*.md")):
        text = f.read_text(encoding="utf-8")
        title = re.search(r"^title: (.*)$", text, re.M).group(1)
        body = text.split("---", 2)[2].strip()
        arts.append({"id": f.stem, "title": title, "content": body})
    return arts


def search_knowledge_base(query: str, top_k: int = 3) -> list:
    words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2}
    scored = []
    for a in _read_kb():
        hay = (a["title"] + " " + a["content"]).lower()
        score = sum(3 for w in words if w in a["title"].lower()) + sum(1 for w in words if w in hay)
        if score:
            scored.append((score, a))
    scored.sort(key=lambda x: -x[0])
    return [a for _, a in scored[:top_k]] or [{"id": None, "title": "No match", "content": "No relevant article found."}]


def check_service_status(service: str) -> dict:
    s = SERVICE_STATUS.get(service.lower().strip())
    return {"service": service, **s} if s else {"service": service, "status": "unknown", "known_services": sorted(SERVICE_STATUS)}


def get_device_info(employee_id: str) -> dict:
    d = DEVICES.get(str(employee_id).strip())
    return {"found": True, "employee_id": employee_id, **d} if d else {"found": False}
