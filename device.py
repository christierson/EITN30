import socket
import functools


def socket_safe(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as e:
            if hasattr(self, "sock"):
                try:
                    self.sock.close()
                except Exception:
                    pass  # Ignore errors during close
            raise e  # Optionally re-raise

    return wrapper


class Mobile:
    def __init__(self, ip):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, 5000))

    @socket_safe
    def send(self, msg: str):
        self.sock.sendall(msg.encode())

    @socket_safe
    def recv(self):
        return self.sock.recv(1024)


class Base:
    def __init__(self, ip):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []
        self.sock.bind((ip, 5000))
        self.sock.listen()
        self.conn, self.addr = self.sock.accept()

    @socket_safe
    def send(self, msg: str):
        self.conn.sendall(msg.encode())

    @socket_safe
    def recv(self):
        return self.conn.recv(1024)
