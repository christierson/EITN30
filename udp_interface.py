import os
import json
import socket
import threading
import math

HEADER_OVERHEAD = 6
MAX_UDP_PACKET_SIZE = 32
MAX_PAYLOAD_SIZE = MAX_UDP_PACKET_SIZE - HEADER_OVERHEAD


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
        self.reassembly_buffer = {}

    def send(self, data: dict):
        json_bytes = json.dumps(data).encode()
        total_len = len(json_bytes)

        if total_len <= MAX_UDP_PACKET_SIZE:
            self.sock.sendto(b"0|1|" + json_bytes, (self.remote_ip, self.remote_port))
        else:
            num_chunks = math.ceil(total_len / MAX_PAYLOAD_SIZE)
            for i in range(num_chunks):
                print(f"sending chunk {i}")
                chunk = json_bytes[i * MAX_PAYLOAD_SIZE : (i + 1) * MAX_PAYLOAD_SIZE]
                header = f"{i}|{num_chunks}|".encode()
                self.sock.sendto(header + chunk, (self.remote_ip, self.remote_port))

    def _parse_chunk_header(self, data: bytes):
        try:
            header, payload = data.split(b"|", 2), None
            if len(header) >= 2:
                chunk_idx = int(header[0])
                total_chunks = int(header[1])
                rest = data.split(b"|", 2)[2]
                return chunk_idx, total_chunks, rest
        except Exception as e:
            print(f"[UDP PARSE ERROR] {e}")
        return None, None, None

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(MAX_UDP_PACKET_SIZE)
                chunk_idx, total_chunks, chunk_data = self._parse_chunk_header(data)
                if chunk_idx is None:
                    continue

                key = addr
                if key not in self.reassembly_buffer:
                    self.reassembly_buffer[key] = [None] * total_chunks

                self.reassembly_buffer[key][chunk_idx] = chunk_data

                if all(self.reassembly_buffer[key]):
                    full_bytes = b"".join(self.reassembly_buffer[key])
                    try:
                        message = json.loads(full_bytes.decode())
                        if self.on_receive:
                            self.on_receive(message, addr)
                    except json.JSONDecodeError as e:
                        print(f"[UDP JSON ERROR] {e}")
                    finally:
                        del self.reassembly_buffer[key]
            except Exception as e:
                print(f"[UDP ERROR] {e}")

    def start_listening(self, on_receive_callback):
        self.on_receive = on_receive_callback
        self.running = True
        self.receiver_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.receiver_thread.start()

    def stop(self):
        self.running = False
        self.sock.close()
