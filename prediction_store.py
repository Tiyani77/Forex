"""Server-side Supabase REST storage. Never put the service-role key in client code."""
import requests
import streamlit as st


def config():
    try:
        url = str(st.secrets['SUPABASE_URL']).rstrip('/')
        key = str(st.secrets['SUPABASE_SERVICE_ROLE_KEY'])
        if not url.startswith('https://') or not key:
            raise ValueError('Invalid Supabase configuration')
        return url, key
    except (KeyError, FileNotFoundError, ValueError):
        return None


def _call(method, path, *, params=None, payload=None):
    cfg = config()
    if not cfg:
        raise RuntimeError('Supabase is not configured in Streamlit Secrets.')
    url, key = cfg
    headers = {'apikey': key, 'Authorization': f'Bearer {key}',
               'Content-Type': 'application/json', 'Prefer': 'return=representation'}
    response = requests.request(method, url + '/rest/v1/' + path,
                                headers=headers, params=params, json=payload, timeout=20)
    if not response.ok:
        # Do not expose URLs, keys or full upstream response bodies to users.
        raise RuntimeError(f'Database request failed (HTTP {response.status_code}). Check SQL table and Secrets.')
    return response.json() if response.content else []


def save_prediction(record):
    return _call('POST', 'forex_predictions', payload=record)


def list_predictions(limit=500):
    return _call('GET', 'forex_predictions', params={
        'select': '*', 'order': 'recorded_at.desc', 'limit': str(limit)
    })


def complete_prediction(record_id, result):
    return _call('PATCH', 'forex_predictions', params={'id': 'eq.' + str(record_id),
        'status': 'eq.pending'}, payload=result)
