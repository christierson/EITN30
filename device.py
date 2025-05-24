import socket
import functools


# # MOBILE

# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.connect(("10.0.0.1", 5000))  # connect to base station on port 5000
# sock.sendall(b"Hello Base Station!")
# response = sock.recv(1024)
# print("Received:", response)
# sock.close()


# # BASE
# server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# server.bind(("10.0.0.1", 5000))
# server.listen()

# conn, addr = server.accept()
# print("Connection from", addr)
# data = conn.recv(1024)
# print("Received:", data)
# conn.sendall(b"Hello Mobile Unit!")
# conn.close()


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


class Device:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @socket_safe
    def send(self, msg: str):
        self.sock.sendall(msg.encode())

    @socket_safe
    def recv(self):
        return self.sock.recv(1024)


class Mobile(Device):
    def __init__(self, ip):
        super().__init__()
        self.sock.connect((ip, 5000))


class Base(Device):
    def __init__(self, ip):
        super().__init__()
        self.connections = []
        self.sock
        self.sock.bind((ip, 5000))

    def start(self):
        self.sock.listen()
        self.conn, self.addr = self.sock.accept()
