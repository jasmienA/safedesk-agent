"""Pure-Python node logic: policy check, escalation, write-back. No LLM calls here."""
from config import REFUND_CAP
from policies import ALL_ACTIONS, ASSIGNMENT_GROUPS, RISKY_ACTIONS, approver_for
from systems import execute_action

STATE_MAP = {"done": "resolved", "denied": "resolved", "escalated": "escalated", "info_requested": "awaiting_info"}


def apply_policy(state: dict) -> dict:
    """Normalise the proposal and decide (in code) whether approval is needed."""
    p = dict(state["proposal"])
    notes = []
    if p.get("action") not in ALL_ACTIONS:
        notes.append(f"Unknown action '{p.get('action')}' replaced with escalate_to_human.")
        p["action"] = "escalate_to_human"
    if p["action"] == "refund":
        amt = p.get("amount")
        if not amt or amt <= 0:
            notes.append("Refund without a valid amount; escalated.")
            p["action"] = "escalate_to_human"
        elif amt > REFUND_CAP:
            notes.append(f"Refund ${amt:,.2f} is above the ${REFUND_CAP:,.0f} cap; routed to Finance Manager.")
            p["action"] = "refund_above_cap_escalate"
    needs = p["action"] in RISKY_ACTIONS
    approver = approver_for(p, state["ticket"]) if needs else None
    return {"proposal": p, "needs_approval": needs, "approver": approver,
            "audit": [{"step": "policy", "action": p["action"], "needs_approval": needs,
                       "approver": approver["name"] if approver else None, "notes": notes}]}


def escalate(state: dict) -> dict:
    """Escalate: triage-level escalations, or an approver rejection."""
    if state.get("approved") is False:
        comment = state.get("approver_comment") or "no comment"
        result = {"status": "escalated", "message": f"Rejected by approver ({comment}). Escalated to a human."}
        return {"result": result, "audit": [{"step": "escalate", "reason": "rejected"}]}
    if state.get("injection_suspected"):
        action = "flag_injection_and_escalate"
    elif state.get("category") == "unclear":
        action = "ask_for_more_info"
    else:
        action = "escalate_to_human"
    proposal = {"action": action, "reason": state.get("triage_reasoning", ""), "kb_ids": ["KB030"],
                "customer_message": ("Could you share more detail about what you need help with?"
                                     if action == "ask_for_more_info" else "")}
    result = execute_action(proposal, state["ticket"])
    return {"proposal": proposal, "needs_approval": False, "result": result,
            "audit": [{"step": "escalate", "action": action}]}


def execute(state: dict) -> dict:
    result = execute_action(state["proposal"], state["ticket"])
    return {"result": result, "audit": [{"step": "execute", "action": state["proposal"]["action"], "status": result["status"]}]}


def build_writeback(state: dict):
    """Returns (fields_to_update, work_note). Same shape the ServiceNow client will use later."""
    p = state.get("proposal", {})
    r = state.get("result", {})
    category = state.get("category", "unclear")
    action = p.get("action")
    if action == "escalate_to_network_team":
        group = "Network Team"
    elif action == "flag_injection_and_escalate":
        group = "Security"
    elif r.get("status") == "escalated":
        group = "Service Desk L2"
    else:
        group = ASSIGNMENT_GROUPS.get(category, "Service Desk")
    lines = [f"[AI triage] category={category}, priority={state.get('priority')}, confidence={state.get('confidence')}"]
    if p:
        lines.append(f"Proposed action: {action}. Reason: {p.get('reason', '')}")
        if p.get("kb_ids"):
            lines.append("KB: " + ", ".join(p["kb_ids"]))
        if p.get("trace"):
            lines.append("Tools used: " + ", ".join(t["tool"] for t in p["trace"]))
    if state.get("needs_approval"):
        who = (state.get("approver") or {}).get("name")
        lines.append(f"Approval by {who}: {'APPROVED' if state.get('approved') else 'REJECTED'}"
                     + (f" ({state.get('approver_comment')})" if state.get("approver_comment") else ""))
    lines.append(f"Result: {r.get('message')}")
    fields = {"category": category, "priority": state.get("priority"), "assignment_group": group,
              "state": STATE_MAP.get(r.get("status"), "escalated"), "close_notes": r.get("message")}
    return fields, "\n".join(lines)
