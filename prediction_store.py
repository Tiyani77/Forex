"""Server-side Supabase REST prediction storage.

Keep SUPABASE_SERVICE_ROLE_KEY in Streamlit Secrets, never in source control.
This module must only be called from trusted server-side code.
"""
from urllib.parse import urlsplit

import requests
import streamlit as st


TABLE = "forex_predictions"


def config():
    try:
        url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
        key = str(st.secrets["SUPABASE_SERVICE_ROLE_KEY"]).strip()
    except (KeyError, FileNotFoundError):
        return None

    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname
            or not parsed.hostname.endswith(".supabase.co")
            or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment or not key):
        raise RuntimeError(
            "Invalid SUPABASE_URL. Use the project base URL ending in .supabase.co "
            "without /rest/v1."
        )
    return url, key


def _headers(key):
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "return=representation",
        "Accept-Profile": "public",
        "Content-Profile": "public",
    }
    # New sb_secret_* keys are API gateway keys, not JWT bearer tokens.
    # Legacy service_role keys are JWTs and can be used as Bearer tokens.
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _safe_error(response):
    status = response.status_code
    code = None
    try:
        body = response.json()
        if isinstance(body, dict):
            code = body.get("code")
    except ValueError:
        pass

    if status == 404 and code in ("PGRST205", "PGRST202"):
        return (
            f"Supabase HTTP 404 ({code}): REST schema cache cannot find the table. "
            "Verify Data API > Exposed tables includes public.forex_predictions, "
            "then refresh the schema cache."
        )
    if status == 404:
        return (
            "Supabase HTTP 404: endpoint not found. Check the project URL, "
            "Data API exposure, and that the Streamlit secrets point to the same project."
        )
    if status in (401, 403):
        return (
            f"Supabase HTTP {status}: authentication or permissions rejected. "
            "Check the server-side secret key and database access policies."
        )
    return f"Supabase request failed (HTTP {status}, code {code or 'unknown'})."


def _call(method, path, *, params=None, payload=None):
    cfg = config()
    if cfg is None:
        raise RuntimeError("Supabase is not configured in Streamlit Secrets.")
    url, key = cfg
    try:
        response = requests.request(
            method,
            f"{url}/rest/v1/{path}",
            headers=_headers(key),
            params=params,
            json=payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        # Do not expose a raw exception: it may contain sensitive URL parameters.
        raise RuntimeError(
            "Could not reach Supabase. Check network access and the project URL."
        ) from None
    if not response.ok:
        raise RuntimeError(_safe_error(response))
    return response.json() if response.content else []


def test_connection():
    """Actually query the table; config() alone does not prove connectivity."""
    _call("GET", TABLE, params={"select": "id", "limit": "1"})
    return True


def save_prediction(record):
    return _call("POST", TABLE, payload=record)


def list_predictions(limit=500):
    return _call("GET", TABLE, params={
        "select": "*", "order": "recorded_at.desc", "limit": str(limit)
    })


def complete_prediction(record_id, result):
    return _call("PATCH", TABLE, params={
        "id": "eq." + str(record_id), "status": "eq.pending"
    }, payload=result)
