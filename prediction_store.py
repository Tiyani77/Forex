
"""
Forex Intelligence V3.3
Supabase Prediction Storage

Server-side only.
Never expose Supabase secret keys in GitHub.
"""

import requests
import streamlit as st
from urllib.parse import urlsplit, urlunsplit


TABLE = "forex_predictions"


def config():
    """
    Read Supabase credentials from Streamlit Secrets.

    Returns (base_url, api_key) or None.
    Compatible with existing app.py.
    """
    try:
        raw_url = str(
            st.secrets.get("SUPABASE_URL", "")
        ).strip()

        api_key = str(
            st.secrets.get(
                "SUPABASE_SERVICE_ROLE_KEY", ""
            )
        ).strip()

        if not raw_url or not api_key:
            return None

        # Normalize accidental duplicate scheme.
        while raw_url.startswith("https://https://"):
            raw_url = raw_url.replace(
                "https://https://",
                "https://",
                1
            )

        raw_url = raw_url.rstrip("/")

        # Remove REST endpoint suffix if supplied.
        if raw_url.endswith("/rest/v1"):
            raw_url = raw_url[:-8]

        parts = urlsplit(raw_url)

        if (
            parts.scheme != "https"
            or not parts.hostname
            or not parts.hostname.endswith(".supabase.co")
            or parts.path not in ("", "/")
        ):
            return None

        base_url = urlunsplit((
            parts.scheme,
            parts.netloc,
            "",
            "",
            ""
        )).rstrip("/")

        return base_url, api_key

    except Exception:
        return None


def _headers(api_key, method="GET"):
    """
    Use the appropriate headers for Supabase keys.
    """
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Legacy JWT keys can be used as bearer tokens.
    if not api_key.startswith("sb_secret_"):
        headers["Authorization"] = (
            f"Bearer {api_key}"
        )

    if method in ("POST", "PATCH"):
        headers["Prefer"] = "return=representation"

    return headers


def _call(
    method,
    path,
    *,
    params=None,
    payload=None
):
    """
    Make a Supabase REST API request.
    """
    settings = config()

    if not settings:
        raise RuntimeError(
            "Supabase configuration is missing or invalid. "
            "Check SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY "
            "in Streamlit Secrets."
        )

    base_url, api_key = settings

    endpoint = (
        f"{base_url}/rest/v1/{path.lstrip('/')}"
    )

    try:
        response = requests.request(
            method=method,
            url=endpoint,
            headers=_headers(api_key, method),
            params=params,
            json=payload,
            timeout=25
        )

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Supabase connection timed out. "
            "Please try again."
        ) from None

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Supabase. "
            "Check the project URL and network."
        ) from None

    except requests.exceptions.RequestException:
        raise RuntimeError(
            "A Supabase network request failed."
        ) from None

    if not response.ok:
        status = response.status_code

        # Safe structured error code only.
        error_code = ""
        try:
            error_code = str(
                response.json().get("code", "")
            )
        except (ValueError, AttributeError):
            pass

        if status == 401:
            message = (
                "Supabase authentication failed. "
                "Check that your secret key belongs "
                "to the correct project."
            )

        elif status == 403:
            message = (
                "Supabase access denied. "
                "Check table privileges and "
                "Row Level Security."
            )

        elif status == 404:
            message = (
                "Supabase REST resource not found. "
                "Check the project URL and confirm "
                "forex_predictions is exposed "
                "through the Data API."
            )

        else:
            message = (
                f"Supabase request failed "
                f"(HTTP {status})."
            )

        if error_code:
            message += f" Error code: {error_code}"

        raise RuntimeError(message)

    if not response.content:
        return []

    try:
        return response.json()
    except ValueError:
        return []


def test_connection():
    """
    Actually query the table to verify connectivity.
    """
    try:
        _call(
            "GET",
            TABLE,
            params={
                "select": "id",
                "limit": "1"
            }
        )
        return True, "Supabase connected successfully."

    except Exception as exc:
        return False, str(exc)


def save_prediction(record):
    """
    Save a new forward prediction.
    """
    if not isinstance(record, dict):
        raise ValueError(
            "Prediction must be a dictionary."
        )

    return _call(
        "POST",
        TABLE,
        payload=record
    )


def list_predictions(limit=500):
    """
    Retrieve saved predictions, newest first.
    """
    limit = max(1, min(int(limit), 1000))

    return _call(
        "GET",
        TABLE,
        params={
            "select": "*",
            "order": "recorded_at.desc",
            "limit": str(limit)
        }
    )


def complete_prediction(record_id, result):
    """
    Update a pending prediction with its outcome.
    """
    if not record_id:
        raise ValueError(
            "Prediction ID is required."
        )

    if not isinstance(result, dict):
        raise ValueError(
            "Prediction result must be a dictionary."
        )

    return _call(
        "PATCH",
        TABLE,
        params={
            "id": f"eq.{record_id}",
            "status": "eq.pending"
        },
        payload=result
    )
