"""Executor: carries out an approved (or non-risky) action on the FAKE systems."""
from data import BILLING, USERS


def _user(uid):
    return USERS.get(str(uid or "").strip())


def execute_action(proposal: dict, ticket: dict) -> dict:
    a = proposal.get("action")
    msg = proposal.get("customer_message") or ""
    target = _user(proposal.get("target_user_id") or ticket.get("caller_id"))

    if a == "reset_password":
        if not target:
            return {"status": "escalated", "message": "Target user not found; escalated."}
        return {"status": "done", "message": f"Temporary password sent to {target['email']} (simulated)."}
    if a == "unlock_account":
        return {"status": "done", "message": f"Account {target['id'] if target else '?'} unlocked (simulated)."}
    if a == "reset_mfa":
        return {"status": "done", "message": f"MFA reset for {target['email'] if target else '?'}; enrol a new device at next sign-in (simulated)."}
    if a == "disable_account":
        if target:
            target["status"] = "disabled"
        return {"status": "done", "message": f"Accounts for {target['name'] if target else '?'} disabled (simulated)."}
    if a == "grant_access":
        return {"status": "done", "message": f"Access to '{proposal.get('resource')}' granted to {target['name'] if target else '?'} (simulated)."}
    if a in ("refund", "refund_above_cap_escalate"):
        amt = proposal.get("amount") or 0
        if a == "refund":
            return {"status": "done", "message": f"Refund of ${amt:,.2f} issued for invoice {proposal.get('invoice_number')} (simulated)."}
        return {"status": "escalated", "message": f"Refund of ${amt:,.2f} routed to the Finance Manager for processing (above cap)."}
    if a == "correct_invoice":
        inv = BILLING["invoices"].get(str(proposal.get("invoice_number")))
        if inv and proposal.get("details"):
            inv["bill_to"] = proposal["details"]
        return {"status": "done", "message": f"Invoice {proposal.get('invoice_number')} corrected (simulated)."}
    if a == "software_install_request":
        return {"status": "done", "message": f"Install request created: {proposal.get('details') or proposal.get('resource')} (simulated)."}
    if a in ("send_invoice_copy", "update_billing_address", "share_kb_steps"):
        return {"status": "done", "message": msg or f"{a} completed (simulated)."}
    if a == "deny_per_policy":
        return {"status": "denied", "message": msg or "Request denied per policy."}
    if a == "ask_for_more_info":
        return {"status": "info_requested", "message": msg or "Asked the requester for more information."}
    if a == "escalate_to_network_team":
        return {"status": "escalated", "message": "Escalated to the Network team."}
    if a == "flag_injection_and_escalate":
        return {"status": "escalated", "message": "Suspected prompt injection. Flagged and escalated to Security. No action taken."}
    if a in ("deny_and_escalate", "escalate_to_human"):
        return {"status": "escalated", "message": msg or "Escalated to Service Desk L2."}
    return {"status": "escalated", "message": f"Unknown action '{a}'. Escalated."}
