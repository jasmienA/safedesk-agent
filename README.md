# Ticket triage agent (Stage 1)

Multi-agent IT/support ticket triage with a human approval gate, running on a mock ticket backend
and fake enterprise systems (users, billing, devices, service status, knowledge base).

## Flow
ticket -> triage (LLM) -> access / billing / technical agent (LLM + tools) -> policy check (code)
-> approval pause if risky -> execute (code) -> write back to the ticket

AI is used for interpreting messy text and choosing tools. Rules, approvals and side effects are plain code.

## Run (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then edit .env: API key and the two model names
python main.py --list
python main.py --ticket T014
python main.py --all --auto-approve
```

## Layout
- `data/` fake systems and `dummy_tickets.csv` (40 labeled tickets, also the eval set)
- `kb/` 17 knowledge base articles
- `tickets/mock.py` ticket backend (a ServiceNow client with the same methods can replace it later)
- `toolkit.py` / `tools.py` tool logic and its LangChain wrappers
- `agents.py` triage classifier and the specialist agent loop
- `policies.py`, `nodes.py`, `systems.py` rules, policy/escalation/write-back logic, fake executor
- `graph.py` LangGraph wiring, including the `interrupt()` approval pause
- `evaluate.py` scoring against expected labels

## Next stages
Postgres checkpointer, FastAPI approval endpoints with signed email links, queue and workers, ServiceNow client, Docker and AWS.
