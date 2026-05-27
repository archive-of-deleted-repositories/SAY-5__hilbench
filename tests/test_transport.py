import threading

from hilbench.server import serve
from hilbench.transport import InProcessTransport, TCPTransport


def test_in_process_transport_roundtrip():
    transport = InProcessTransport()
    assert transport.send("PING") == "OK PONG"
    transport.close()


def test_tcp_transport_roundtrip():
    import socketserver

    from hilbench.server import _Handler

    server = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = TCPTransport(host, port)
        assert client.send("PING") == "OK PONG"
        assert client.send("STATUS") == "OK state=IDLE speed=0"
        client.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_serve_is_importable():
    assert callable(serve)
