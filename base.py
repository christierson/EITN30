import socket
import threading
import queue
from utils import socket_safe


class Base:
    def __init__(self, ip="10.0.0.1", port=5000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((ip, port))
        self.sock.listen()
        self.conn = None
        self.addr = None
        self.send_queue = queue.Queue()
        self.stop_event = threading.Event()

    def accept(self):
        self.conn, self.addr = self.sock.accept()
        print(f"[Base] Connection from {self.addr}")
        threading.Thread(target=self._recv_loop, daemon=True).start()
        threading.Thread(target=self._send_loop, daemon=True).start()

    def send(self, msg: str):
        self.send_queue.put(msg)

    @socket_safe
    def _send_loop(self):
        while not self.stop_event.is_set():
            try:
                msg = self.send_queue.get(timeout=1)
                self.conn.sendall(msg.encode())
            except queue.Empty:
                continue

    @socket_safe
    def _recv_loop(self):
        while not self.stop_event.is_set():
            data = self.conn.recv(1024)
            if data:
                print("[Base] Received:", data.decode())
            else:
                break  # connection closed

    def close(self):
        self.stop_event.set()
        if self.conn:
            self.conn.close()
        self.sock.close()


class BaseStation(Base):
    def __init__():
        pass
