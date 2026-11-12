"""Run the ticket triage agent on the dummy tickets.

  python main.py --list                      show the tickets
  python main.py --ticket T014               run one ticket (asks you to approve risky actions)
  python main.py --ticket T014 T020 T033     run several
  python main.py --all --auto-approve        run everything and score it against the expected labels
  python main.py --diagram                   print the graph as a Mermaid diagram
"""
import argparse
import json
import time
import uuid

import config
from data import USERS
from evaluate import score, summarize
from tickets.mock import MockBackend

TICKET_FIELDS = ("id", "caller_id", "short_description", "description")


def show_list(backend):
    print(f"{'ID':5} {'CALLER':22} {'SUBJECT':44} {'EXPECTED':26} APPROVAL")
    for tid, t in backend.tickets.items():
        e = backend.get_expected(tid)
        caller = USERS.get(t["caller_id"], {}).get("name", t["caller_id"])
        print(f"{tid:5} {caller[:21]:22} {t['short_description'][:43]:44} {e['expected_action'][:25]:26} {e['needs_approval']}")


def ask_console(payload, auto_approve):
    print("\n  >>> APPROVAL NEEDED")
    print(f"      action   : {payload['action']} {payload['details']}")
    print(f"      reason   : {payload['reason']}")
    print(f"      approver : {payload['approver']['name']} ({payload['approver']['role']})")
    if auto_approve:
        print("      (auto-approved)")
        return {"approved": True, "comment": "auto-approved for test run"}
    ans = input("      Approve? [y/n]: ").strip().lower()
    return {"approved": ans.startswith("y"), "comment": "" if ans.startswith("y") else "rejected in console"}


def run_ticket(app, backend, tid, auto_approve):
    import agents
    from langgraph.types import Command
    ticket = {k: backend.get_ticket(tid)[k] for k in TICKET_FIELDS}  # no expected labels leak to the agents
    cfg = {"configurable": {"thread_id": f"{tid}-{uuid.uuid4().hex[:6]}"}}
    agents.reset_usage()
    app.invoke({"ticket": ticket, "audit": []}, cfg)
    while True:
        snap = app.get_state(cfg)
        if not snap.next:
            break
        decision = ask_console(snap.tasks[0].interrupts[0].value, auto_approve)
        app.invoke(Command(resume=decision), cfg)
    values = app.get_state(cfg).values
    values["usage"] = dict(agents.USAGE)
    return values


def print_result(tid, ticket, v):
    p = v.get("proposal", {})
    print(f"\n=== {tid}: {ticket['short_description']}")
    print(f"  triage   : {v.get('category')} / {v.get('priority')} / confidence {v.get('confidence')}"
          + ("  [injection suspected]" if v.get("injection_suspected") else ""))
    if p.get("trace"):
        print("  tools    : " + " -> ".join(t["tool"] for t in p["trace"]))
    print(f"  proposed : {p.get('action')}  ({p.get('reason', '')[:110]})")
    if v.get("needs_approval"):
        print(f"  approval : {'APPROVED' if v.get('approved') else 'REJECTED'} by {v['approver']['name']}")
    print(f"  result   : {v['result']['status']}: {v['result']['message']}")
    u = v["usage"]
    print(f"  usage    : {u['calls']} LLM calls, {u['input']} in / {u['output']} out tokens")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ticket", nargs="+")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--auto-approve", action="store_true")
    ap.add_argument("--diagram", action="store_true")
    args = ap.parse_args()

    backend = MockBackend(config.DATA_DIR / "dummy_tickets.csv")
    if args.list:
        return show_list(backend)

    config.require_models()
    from langgraph.checkpoint.memory import MemorySaver
    from graph import build_graph
    app = build_graph(backend, MemorySaver())
    if args.diagram:
        return print(app.get_graph().draw_mermaid())

    ids = args.ticket or (list(backend.tickets)[: args.limit] if args.all else [])
    if not ids:
        return ap.print_help()

    rows = []
    for tid in ids:
        values = run_ticket(app, backend, tid, args.auto_approve)
        print_result(tid, backend.get_ticket(tid), values)
        s = score(backend.get_expected(tid), values)
        rows.append({"id": tid, **s, "action": values["proposal"]["action"],
                     "tokens": values["usage"]["input"] + values["usage"]["output"]})
        misses = [k.replace("_ok", "") for k, ok in s.items() if not ok]
        if misses:
            e = backend.get_expected(tid)
            print(f"  vs expected: {e['expected_category']}/{e['expected_priority']}/{e['expected_action']}  -> mismatch: {', '.join(misses)}")

    if len(rows) > 1:
        print("\n=== SUMMARY (% matching expected labels) ===")
        for k, v in summarize(rows).items():
            print(f"  {k.replace('_ok', ''):10}: {v}%")
        print(f"  tickets   : {len(rows)}, total tokens: {sum(r['tokens'] for r in rows)}")
    config.RESULTS_DIR.mkdir(exist_ok=True)
    out = config.RESULTS_DIR / f"run_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
