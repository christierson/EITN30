# import os
# import json
# import socket
# import threading


# class UDPInterface:
#     def __init__(
#         self,
#         local_port: int = 5005,
#         remote_port: int = 5005,
#         config_path="device_config.json",
#     ):
#         self.local_port = local_port
#         self.remote_port = remote_port

#         is_base = os.getenv("IS_BASE", "false").lower() == "true"
#         self.role = "base" if is_base else "mobile"
#         self.peer_role = "mobile" if is_base else "base"

#         with open(config_path, "r") as f:
#             config = json.load(f)

#         self.local_ip = config[self.role]["ip"]
#         self.remote_ip = config[self.peer_role]["ip"]

#         print(
#             f"[UDP] Role: {self.role.upper()}, Local IP: {self.local_ip}, Remote IP: {self.remote_ip}"
#         )

#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.sock.bind((self.local_ip, self.local_port))

#         self.running = False
#         self.receiver_thread = None
#         self.on_receive = None

#     def send(self, data: bytes):
#         self.sock.sendto(data, (self.remote_ip, self.remote_port))

#     def receive(self, bufsize=1024) -> tuple[bytes, tuple]:
#         return self.sock.recvfrom(bufsize)

#     def start_listening(self, on_receive_callback):
#         self.on_receive = on_receive_callback
#         self.running = True
#         self.receiver_thread = threading.Thread(target=self._listen_loop, daemon=True)
#         self.receiver_thread.start()

#     def _listen_loop(self):
#         while self.running:
#             try:
#                 data, addr = self.sock.recvfrom(1024)
#                 if self.on_receive:
#                     self.on_receive(data, addr)
#             except Exception as e:
#                 print(f"[UDP ERROR] {e}")

#     def stop(self):
#         self.running = False
#         self.sock.close()


import os
import json
import socket
import threading
import math

MAX_UDP_PACKET_SIZE = 1024  # bytes per packet


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
        """Encode dict as JSON and send (with chunking if needed)."""
        json_bytes = json.dumps(data).encode()
        total_len = len(json_bytes)

        if total_len <= MAX_UDP_PACKET_SIZE:
            self.sock.sendto(b"0|1|" + json_bytes, (self.remote_ip, self.remote_port))
        else:
            num_chunks = math.ceil(total_len / MAX_UDP_PACKET_SIZE)
            for i in range(num_chunks):
                chunk = json_bytes[
                    i * MAX_UDP_PACKET_SIZE : (i + 1) * MAX_UDP_PACKET_SIZE
                ]
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
                data, addr = self.sock.recvfrom(2048)
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
        """Register callback that receives decoded dict and sender address."""
        self.on_receive = on_receive_callback
        self.running = True
        self.receiver_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.receiver_thread.start()

    def stop(self):
        self.running = False
        self.sock.close()
