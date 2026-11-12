"""Mock ticket backend loaded from data/dummy_tickets.csv.

It has the same methods the ServiceNow client will have later, so the agents never
know which one they are talking to.
"""
import csv

EXPECTED_FIELDS = ("expected_category", "expected_priority", "expected_action", "needs_approval", "expected_kb")


class MockBackend:
    def __init__(self, csv_path):
        self.tickets, self.expected = {}, {}
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                tid = row["id"]
                self.tickets[tid] = {"id": tid, "caller_id": row["caller_id"],
                                     "short_description": row["short_description"],
                                     "description": row["description"],
                                     "state": "new", "work_notes": []}
                self.expected[tid] = {k: row[k] for k in EXPECTED_FIELDS}

    # --- interface (ServiceNow version later: GET / PATCH on /api/now/table/incident) ---
    def get_new_tickets(self, limit=50):
        return [t for t in self.tickets.values() if t["state"] == "new"][:limit]

    def get_ticket(self, ticket_id):
        return self.tickets[ticket_id]

    def update_ticket(self, ticket_id, fields):
        self.tickets[ticket_id].update(fields)

    def add_work_note(self, ticket_id, note):
        self.tickets[ticket_id]["work_notes"].append(note)

    # --- used only by the evaluation code, never shown to the agents ---
    def get_expected(self, ticket_id):
        return self.expected[ticket_id]
