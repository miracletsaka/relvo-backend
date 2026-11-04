
"""Small Retell API helpers (Bearer auth). Phase 1 only checks credentials; calls come in Phase 2."""
import requests

BASE = "https://api.retellai.com"


def _get(path: str, api_key: str) -> requests.Response:
    return requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {api_key}"}, timeout=20)


def check_agent(api_key: str, agent_id: str) -> tuple[bool, str]:
    r = _get(f"/get-agent/{agent_id}", api_key)
    if r.status_code == 200:
        return True, r.json().get("agent_name") or "Agent found"
    if r.status_code == 401:
        return False, "Retell rejected the API key."
    if r.status_code == 404:
        return False, "Agent ID not found in this Retell account."
    return False, f"Retell error {r.status_code}"


def check_number(api_key: str, number: str) -> tuple[bool, str]:
    r = _get(f"/get-phone-number/{number}", api_key)
    if r.status_code == 200:
        return True, r.json().get("phone_number_pretty") or number
    if r.status_code == 404:
        return False, "This number is not in your Retell account."
    return False, f"Retell error {r.status_code}"