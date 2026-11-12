"""Rules that must never depend on an LLM's judgment."""
from data import USERS

# Actions each specialist is allowed to propose.
ALLOWED_ACTIONS = {
    "access": ["reset_password", "unlock_account", "grant_access", "reset_mfa", "disable_account",
               "share_kb_steps", "deny_and_escalate", "escalate_to_human", "ask_for_more_info",
               "flag_injection_and_escalate"],
    "billing": ["refund", "refund_above_cap_escalate", "correct_invoice", "send_invoice_copy",
                "update_billing_address", "deny_per_policy", "share_kb_steps", "escalate_to_human",
                "ask_for_more_info", "flag_injection_and_escalate"],
    "technical": ["share_kb_steps", "software_install_request", "escalate_to_network_team",
                  "escalate_to_human", "ask_for_more_info", "flag_injection_and_escalate"],
}
ALL_ACTIONS = sorted({a for v in ALLOWED_ACTIONS.values() for a in v})

# Actions that change something important: they pause for human approval.
RISKY_ACTIONS = {"reset_password", "unlock_account", "grant_access", "reset_mfa", "disable_account",
                 "refund", "refund_above_cap_escalate", "correct_invoice", "software_install_request"}

# Treated as the same outcome when scoring against the expected labels.
ESCALATE_FAMILY = {"escalate_to_human", "deny_and_escalate"}

ACCESS_POLICY = {
    "password_reset": {"who_can_request": "account owner only (caller must equal the account)",
                       "account_must_be_active": True, "approval_required": True,
                       "on_behalf_of_others": "never allowed", "kb": "KB010"},
    "account_unlock": {"who_can_request": "account owner only", "account_must_be_active": True,
                       "approval_required": True, "kb": "KB011"},
    "mfa_reset": {"who_can_request": "account owner only", "account_must_be_active": True,
                  "approval_required": True, "kb": "KB013"},
    "grant_access": {"requires": "a named resource and manager/data-owner approval",
                     "verbal_approval_valid": False, "kb": "KB012"},
    "local_admin": {"granted": False, "alternative": "software request process (KB006) or escalate", "kb": "KB012"},
    "disable_account": {"who_can_request": "the leaver's manager or HR", "approval_required": True, "kb": "KB014"},
}

ASSIGNMENT_GROUPS = {"access": "Identity & Access", "billing": "Finance Support", "technical": "Service Desk"}


def _person(user_id):
    u = USERS[user_id]
    return {"name": u["name"], "email": u["email"], "role": u["title"]}


SERVICE_DESK_LEAD = {"name": "Service Desk Lead", "email": "servicedesk.lead@acme.example", "role": "Service Desk Lead"}


def approver_for(proposal, ticket):
    """Who has to approve this action (code, not LLM)."""
    action = proposal.get("action")
    if action in {"refund", "refund_above_cap_escalate", "correct_invoice"}:
        return _person("20101")  # Finance Manager
    if action == "grant_access":
        resource = (proposal.get("resource") or "").lower()
        if "payroll" in resource:
            return _person("20001")  # CFO
        if "finance" in resource:
            return _person("20101")
    if action in {"grant_access", "software_install_request"}:
        caller = USERS.get(ticket.get("caller_id", ""), {})
        mgr = caller.get("manager_id")
        if mgr in USERS:
            return _person(mgr)
    return SERVICE_DESK_LEAD
