"""TAC-03: domyślny `uv run pytest` blokuje sieć (pytest-recording --block-network)."""

import socket

import pytest


def test_socket_connection_is_blocked():
    with pytest.raises(Exception):  # noqa: B017 - typ błędu zależy od wtyczki
        socket.create_connection(("openrouter.ai", 443), timeout=2)
