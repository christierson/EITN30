import os
import json
import socket
import threading


class UDPInterface:
    def __init__(
        self,
        local_port: int = 5005,
        remote_port: int = 5005,
        config_path="device_config.json",
    ):
        self.local_port = local_port
        self.remote_port = remote_port

        is_base = os.getenv("IS_BASE", "false").lower() == "true"
        self.role = "base" if is_base else "mobile"
        self.peer_role = "mobile" if is_base else "base"

        with open(config_path, "r") as f:
            config = json.load(f)

        self.local_ip = config[self.role]["ip"]
        self.remote_ip = config[self.peer_role]["ip"]

        print(
            f"[UDP] Role: {self.role.upper()}, Local IP: {self.local_ip}, Remote IP: {self.remote_ip}"
        )

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, self.local_port))

        self.running = False
        self.receiver_thread = None
        self.on_receive = None

    def send(self, data: bytes):
        self.sock.sendto(data, (self.remote_ip, self.remote_port))

    def receive(self, bufsize=1024) -> tuple[bytes, tuple]:
        return self.sock.recvfrom(bufsize)

    def start_listening(self, on_receive_callback):
        self.on_receive = on_receive_callback
        self.running = True
        self.receiver_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.receiver_thread.start()

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if self.on_receive:
                    self.on_receive(data, addr)
            except Exception as e:
                print(f"[UDP ERROR] {e}")

    def stop(self):
        self.running = False
        self.sock.close()
