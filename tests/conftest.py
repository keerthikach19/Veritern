import inspect
import socket

import pytest

from veritern.config import Settings


@pytest.fixture(autouse=True)
def no_network(monkeypatch, request):
    if request.node.get_closest_marker("live"):
        pytest.skip("Live tests require explicit operator smoke command")

    original_connect = socket.socket.connect

    def blocked(sock, address):
        # Windows asyncio implements socketpair using a local TCP self-pipe.
        # Permit only that stdlib call, never application network connections.
        if any(
            frame.function == "_fallback_socketpair" and frame.filename.endswith("socket.py")
            for frame in inspect.stack()
        ):
            return original_connect(sock, address)
        raise AssertionError("Offline test attempted network access")

    def blocked_dns(*args, **kwargs):
        raise AssertionError("Offline test attempted DNS access")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked_dns)


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, storage_dir=tmp_path / "private", search_backend="manual")
