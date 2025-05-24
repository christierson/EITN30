import socket
import threading
import queue
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


class Device:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.send_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.recv_thread = None
        self.send_thread = None

    def start_threads(self):
        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.recv_thread.start()
        self.send_thread.start()

    def stop_threads(self):
        self.stop_event.set()
        if hasattr(self, "conn") and self.conn:
            self.conn.close()
        else:
            self.sock.close()

    def send(self, msg: str):
        self.send_queue.put(msg)

    @socket_safe
    def _send_loop(self):
        while not self.stop_event.is_set():
            try:
                msg = self.send_queue.get(timeout=1)
                sock = self._active_socket()
                sock.sendall(msg.encode())
            except queue.Empty:
                continue

    @socket_safe
    def _recv_loop(self):
        while not self.stop_event.is_set():
            sock = self._active_socket()
            try:
                data = sock.recv(1024)
                if data:
                    print(f"[{self.__class__.__name__}] Received:", data.decode())
                else:
                    break  # connection closed
            except OSError:
                break

    def _active_socket(self):
        return self.conn if hasattr(self, "conn") and self.conn else self.sock


class Mobile:
    def __init__(self, ip):
        super().__init__()
        self.sock.connect((ip, 5000))

    @socket_safe
    def _send_loop(self):
        while not self.stop_event.is_set():
            try:
                msg = self.send_queue.get(timeout=1)
                sock = self._active_socket()
                sock.sendall(msg.encode())
            except queue.Empty:
                continue

    @socket_safe
    def _recv_loop(self):
        while not self.stop_event.is_set():
            sock = self._active_socket()
            try:
                data = sock.recv(1024)
                if data:
                    print(f"[{self.__class__.__name__}] Received:", data.decode())
                else:
                    break  # connection closed
            except OSError:
                break


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
