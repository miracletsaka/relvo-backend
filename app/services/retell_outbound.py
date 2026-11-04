"""Small Retell API helpers (Bearer auth): credential checks and outbound call creation."""
import requests

BASE = "https://api.retellai.com"


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def _get(path: str, api_key: str) -> requests.Response:
    return requests.get(f"{BASE}{path}", headers=_headers(api_key), timeout=20)


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


def create_call(
    api_key: str,
    agent_id: str,
    from_number: str,
    to_number: str,
    variables: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    """Start an outbound phone call. Returns Retell's JSON (call_id, call_status, ...).

    Raises RuntimeError with Retell's response text on failure, which the
    router stores in outbound_calls.error.
    """
    body = {
        "from_number": from_number,
        "to_number": to_number,
        "override_agent_id": agent_id,
        "retell_llm_dynamic_variables": {k: str(v or "") for k, v in (variables or {}).items()},
        "metadata": metadata or {},
    }
    try:
        r = requests.post(
            f"{BASE}/v2/create-phone-call",
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Could not reach Retell: {e}") from e

    if r.status_code not in (200, 201):
        raise RuntimeError(f"Retell error {r.status_code}: {r.text[:300]}")
    return r.json()