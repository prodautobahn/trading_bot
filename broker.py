"""
Alpaca broker wrapper. Handles orders, positions, account data.
"""

import time
import logging
import requests
import pytz
from datetime import datetime
import config

log = logging.getLogger(__name__)

BASE_URL = config.ALPACA['BASE_URL']
API_KEY = config.ALPACA['API_KEY']
API_SECRET = config.ALPACA['API_SECRET']
HEADERS = {
    'APCA-API-KEY-ID': API_KEY,
    'APCA-API-SECRET-KEY': API_SECRET,
}

def _get(url, params=None):
    r = requests.get(f"{BASE_URL}{url}", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()

def _post(url, data):
    r = requests.post(f"{BASE_URL}{url}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()

def get_account():
    """Return account dictionary."""
    return _get('/v2/account')

def get_position(symbol):
    """Return position for symbol or None."""
    try:
        return _get(f'/v2/positions/{symbol}')
    except requests.HTTPError as exc:
        if exc.response.status_code == 404:
            return None
        raise

def place_order(symbol, qty, side, type_, time_in_force, limit_price=None):
    """
    Place a market order and return order ID.
    """
    data = {
        'symbol': symbol,
        'qty': qty,
        'side': side,
        'type': type_,
        'time_in_force': time_in_force,
    }
    if limit_price is not None:
        data['limit_price'] = limit_price

    log.info(f"Placing order: {data}")
    try:
        resp = _post('/v2/orders', data)
        return resp['id']
    except requests.HTTPError as e:
        log.error(f"Order failed: {e}")
        raise

def get_order(order_id):
    """Return order status."""
    return _get(f'/v2/orders/{order_id}')

def cancel_order(order_id):
    """Cancel order."""
    _post(f'/v2/orders/{order_id}/cancel', {})

def wait_for_filled(order_id, timeout=30):
    """
    Poll order status until filled or timeout.
    Returns order details or raises TimeoutError.
    """
    start = time.time()
    while time.time() - start < timeout:
        order = get_order(order_id)
        if order['status'] in ('filled', 'partially_filled'):
            return order
        if order['status'] in ('canceled', 'expired'):
            raise RuntimeError(f"Order {order_id} {order['status']}")
        time.sleep(1)
    raise TimeoutError(f"Order {order_id} not filled in {timeout}s")

def get_current_price(symbol):
    """Return the latest quote price."""
    data = _get('/v2/stocks/{}/quote'.format(symbol))
    return data['last_price']

# Helper to get the timestamp in server time
def to_server_timestamp(dt):
    tz = pytz.timezone(config.ALPACA['TIME_ZONE'])
    return dt.astimezone(tz).strftime('%Y-%m-%dT%H:%M:%SZ')
