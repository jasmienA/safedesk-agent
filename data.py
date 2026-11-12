import json
from config import DATA_DIR


def _load(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


USERS = _load("users.json")
BILLING = _load("billing.json")
DEVICES = _load("devices.json")
SERVICE_STATUS = _load("service_status.json")
