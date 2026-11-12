"""LangGraph wiring: triage -> specialist -> policy -> (approval pause) -> execute -> write back."""
import operator
from typing import Annotated, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

import agents
import config
import nodes


class TicketState(TypedDict, total=False):
    ticket: dict
    category: str
    priority: str
    confidence: float
    injection_suspected: bool
    triage_reasoning: str
    proposal: dict
    needs_approval: bool
    approver: Optional[dict]
    approved: Optional[bool]
    approver_comment: str
    result: dict
    audit: Annotated[list, operator.add]


def build_graph(backend, checkpointer):
    def triage_node(state):
        t = agents.triage_ticket(state["ticket"])
        return {"category": t.category, "priority": t.priority, "confidence": t.confidence,
                "injection_suspected": t.injection_suspected, "triage_reasoning": t.reasoning,
                "audit": [{"step": "triage", "category": t.category, "priority": t.priority,
                           "confidence": t.confidence, "injection": t.injection_suspected}]}

    def make_specialist(kind):
        def node(state):
            triage = {"category": state["category"], "priority": state["priority"]}
            proposal = agents.run_specialist(kind, state["ticket"], triage)
            return {"proposal": proposal,
                    "audit": [{"step": kind, "action": proposal["action"],
                               "tools": [t["tool"] for t in proposal.get("trace", [])]}]}
        return node

    def policy_node(state):
        return nodes.apply_policy(state)

    def approval_node(state):
        p = state["proposal"]
        # Graph pauses here and its state is checkpointed. It resumes when someone calls
        # app.invoke(Command(resume={...}), config) with the decision.
        decision = interrupt({
            "ticket_id": state["ticket"]["id"], "caller_id": state["ticket"]["caller_id"],
            "action": p["action"],
            "details": {k: p.get(k) for k in ("target_user_id", "amount", "invoice_number", "resource", "details") if p.get(k)},
            "reason": p.get("reason"), "approver": state["approver"],
        })
        return {"approved": bool(decision.get("approved")), "approver_comment": decision.get("comment", ""),
                "audit": [{"step": "approval", "approved": bool(decision.get("approved")),
                           "by": (state["approver"] or {}).get("name")}]}

    def execute_node(state):
        return nodes.execute(state)

    def escalate_node(state):
        return nodes.escalate(state)

    def writeback_node(state):
        fields, note = nodes.build_writeback(state)
        backend.update_ticket(state["ticket"]["id"], fields)
        backend.add_work_note(state["ticket"]["id"], note)
        return {"audit": [{"step": "writeback", "state": fields["state"], "group": fields["assignment_group"]}]}

    def route_after_triage(state):
        if state.get("injection_suspected"):
            return "escalate"
        if state["category"] in ("other", "unclear") or state["confidence"] < config.CONFIDENCE_THRESHOLD:
            return "escalate"
        return state["category"]

    def route_after_policy(state):
        return "approval" if state["needs_approval"] else "execute"

    def route_after_approval(state):
        return "execute" if state["approved"] else "escalate"

    g = StateGraph(TicketState)
    g.add_node("triage", triage_node)
    for kind in ("access", "billing", "technical"):
        g.add_node(kind, make_specialist(kind))
    g.add_node("policy", policy_node)
    g.add_node("approval", approval_node)
    g.add_node("execute", execute_node)
    g.add_node("escalate", escalate_node)
    g.add_node("writeback", writeback_node)

    g.add_edge(START, "triage")
    g.add_conditional_edges("triage", route_after_triage,
                            {"access": "access", "billing": "billing", "technical": "technical", "escalate": "escalate"})
    for kind in ("access", "billing", "technical"):
        g.add_edge(kind, "policy")
    g.add_conditional_edges("policy", route_after_policy, {"approval": "approval", "execute": "execute"})
    g.add_conditional_edges("approval", route_after_approval, {"execute": "execute", "escalate": "escalate"})
    g.add_edge("execute", "writeback")
    g.add_edge("escalate", "writeback")
    g.add_edge("writeback", END)
    return g.compile(checkpointer=checkpointer)
