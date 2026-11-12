"""LangChain tool wrappers. The docstrings are what the LLM reads to decide when to call each tool."""
from langchain_core.tools import tool

import toolkit


@tool
def lookup_user(employee_id: str) -> dict:
    """Look up an employee or customer by id. Returns name, email, department, title, manager, and status (active, on_leave, terminated)."""
    return toolkit.lookup_user(employee_id)


@tool
def check_access_policy(topic: str) -> dict:
    """Get the access rules for a topic. Topics: password_reset, account_unlock, mfa_reset, grant_access, local_admin, disable_account."""
    return toolkit.check_access_policy(topic)


@tool
def check_manager_approval(requester_id: str) -> dict:
    """Find the manager of a requester, who would approve access requests."""
    return toolkit.check_manager_approval(requester_id)


@tool
def get_invoice(invoice_number: str) -> dict:
    """Get an invoice by number: customer, amount, date, status."""
    return toolkit.get_invoice(invoice_number)


@tool
def get_payment_history(customer_id: str) -> dict:
    """Get all payments, subscriptions and invoices for a customer id."""
    return toolkit.get_payment_history(customer_id)


@tool
def check_refund_policy(amount: float, purchase_date: str) -> dict:
    """Check a refund against policy. purchase_date is YYYY-MM-DD. Returns the ruling: allowed_with_approval, needs_finance_manager, or denied_outside_window."""
    return toolkit.check_refund_policy(amount, purchase_date)


@tool
def search_knowledge_base(query: str) -> list:
    """Search the knowledge base articles. Returns up to 3 articles with id, title and content."""
    return toolkit.search_knowledge_base(query)


@tool
def check_service_status(service: str) -> dict:
    """Check if a service is operational. Services: vpn, email, wifi, printing, sso, billing_portal, intranet."""
    return toolkit.check_service_status(service)


@tool
def get_device_info(employee_id: str) -> dict:
    """Get the laptop details of an employee: model, OS, age, free disk space, last patch date."""
    return toolkit.get_device_info(employee_id)


TOOLSETS = {
    "access": [lookup_user, check_access_policy, check_manager_approval, search_knowledge_base],
    "billing": [lookup_user, get_invoice, get_payment_history, check_refund_policy, search_knowledge_base],
    "technical": [search_knowledge_base, check_service_status, get_device_info, lookup_user],
}
