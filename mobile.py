import socket
import threading
import queue
from utils import socket_safe


class Mobile:
    def __init__(self, ip, port=5000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        self.send_queue = queue.Queue()
        self.stop_event = threading.Event()

    def start(self):
        threading.Thread(target=self._recv_loop, daemon=True).start()
        threading.Thread(target=self._send_loop, daemon=True).start()

    def send_message(self, msg: str):
        self.send_queue.put(msg)

    @socket_safe
    def _send_loop(self):
        while not self.stop_event.is_set():
            try:
                msg = self.send_queue.get(timeout=1)
                self.sock.sendall(msg.encode())
            except queue.Empty:
                continue

    @socket_safe
    def _recv_loop(self):
        while not self.stop_event.is_set():
            data = self.sock.recv(1024)
            if data:
                print("[Mobile] Received:", data.decode())
            else:
                break  # socket closed

    def close(self):
        self.stop_event.set()
        self.sock.close()
