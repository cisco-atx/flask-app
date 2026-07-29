"""Shared Flask extension instances.

Path: app/modules/extensions.py
"""
from flask_socketio import SocketIO

# threading mode avoids eventlet/gevent (fragile on Python 3.14)
# and works with the dev server; transport negotiation handles WS upgrade.
socketio = SocketIO(async_mode="threading", cors_allowed_origins="*")