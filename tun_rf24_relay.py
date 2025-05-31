# # #!/home/pi/.env/bin/python3

# # import fcntl
# # import struct
# # import select
# # import threading
# # import queue
# # import os
# # import time
# # import zlib
# # from pyrf24 import RF24, RF24_PA_LOW


# # PAYLOAD_SIZE = 32
# # CHUNK_DATA_SIZE = 28
# # ACK_TIMEOUT = 0.3
# # MAX_RETRIES = 5
# # IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
# # MY_ADDR = b"1Node" if IS_BASE else b"2Node"
# # PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
# # TX_CE = 17
# # TX_CSN = 8
# # RX_CE = 27
# # RX_CSN = 18


# # class RF24ReliableInterface:
# #     def __init__(
# #         self,
# #         tx_ce=TX_CE,
# #         rx_ce=RX_CE,
# #         tx_csn=TX_CSN,
# #         rx_csn=RX_CSN,
# #         tx_addr=MY_ADDR,
# #         rx_addr=PEER_ADDR,
# #     ):

# #         self.tx_radio = RF24(tx_ce, tx_csn)
# #         self.rx_radio = RF24(rx_ce, rx_csn)
# #         self.tx_addr = tx_addr
# #         self.rx_addr = rx_addr

# #         self.tx_radio.begin()
# #         self.rx_radio.begin()

# #         self.tx_radio.setPALevel(RF24_PA_LOW)
# #         self.rx_radio.setPALevel(RF24_PA_LOW)

# #         self.tx_radio.setPayloadSize(PAYLOAD_SIZE)
# #         self.rx_radio.setPayloadSize(PAYLOAD_SIZE)

# #         self.tx_radio.setChannel(76)
# #         self.rx_radio.setChannel(76)

# #         self.tx_radio.openWritingPipe(tx_addr)
# #         self.rx_radio.openReadingPipe(1, rx_addr)
# #         self.rx_radio.startListening()

# #         self.send_queue = queue.Queue()
# #         self.recv_queue = queue.Queue()

# #         self.running = True
# #         self.msg_id = 0
# #         self.incoming_buffers = {}  # msg_id -> list of chunks

# #         self.tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
# #         self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)

# #         self.tx_thread.start()
# #         self.rx_thread.start()

# #     def stop(self):
# #         self.running = False
# #         self.tx_thread.join()
# #         self.rx_thread.join()

# #     def send(self, data: bytes):
# #         self.send_queue.put(data)

# #     def receive(self):
# #         try:
# #             return self.recv_queue.get_nowait()
# #         except queue.Empty:
# #             return None

# #     def _tx_loop(self):
# #         while self.running:
# #             try:
# #                 data = self.send_queue.get(timeout=0.1)
# #             except queue.Empty:
# #                 continue

# #             msg_id = self.msg_id
# #             self.msg_id = (self.msg_id + 1) % 256
# #             chunks = self._chunk_message(data, msg_id)
# #             checksum = zlib.crc32(data).to_bytes(4, "big")

# #             for attempt in range(MAX_RETRIES):
# #                 for chunk in chunks:
# #                     self.tx_radio.write(chunk)
# #                     time.sleep(0.005)

# #                 # Wait for ACK
# #                 start = time.time()
# #                 ack_received = False
# #                 while time.time() - start < ACK_TIMEOUT:
# #                     if self.rx_radio.available():
# #                         ack = self.rx_radio.read(PAYLOAD_SIZE)
# #                         if ack[:3] == b"ACK" and ack[3] == msg_id:
# #                             if ack[4:8] == checksum:
# #                                 ack_received = True
# #                                 break
# #                     time.sleep(0.005)
# #                 if ack_received:
# #                     break
# #                 print(f"[!] Resending msg_id {msg_id}")
# #             else:
# #                 print(f"[X] Failed to send msg_id {msg_id} after retries")

# #     def _rx_loop(self):
# #         while self.running:
# #             if self.rx_radio.available():
# #                 chunk = self.rx_radio.read(PAYLOAD_SIZE)
# #                 if chunk[:3] == b"ACK":
# #                     continue  # Skip ACKs, they're for TX thread

# #                 msg_id, seq, final, length = chunk[0], chunk[1], chunk[2], chunk[3]
# #                 payload = chunk[4 : 4 + length]

# #                 buffer = self.incoming_buffers.setdefault(msg_id, {})
# #                 buffer[seq] = payload

# #                 if final == 1:
# #                     # Assemble full message
# #                     parts = [buffer[i] for i in sorted(buffer.keys())]
# #                     full_data = b"".join(parts)
# #                     try:
# #                         checksum = zlib.crc32(full_data).to_bytes(4, "big")
# #                         ack = b"ACK" + bytes([msg_id]) + checksum
# #                         self.tx_radio.write(ack)
# #                         self.recv_queue.put(full_data)
# #                     except Exception as e:
# #                         print(f"[!] Failed to process full message: {e}")
# #                     del self.incoming_buffers[msg_id]
# #             time.sleep(0.002)

# #     def _chunk_message(self, data: bytes, msg_id: int):
# #         chunks = []
# #         for seq, i in enumerate(range(0, len(data), CHUNK_DATA_SIZE)):
# #             part = data[i : i + CHUNK_DATA_SIZE]
# #             is_final = 1 if (i + CHUNK_DATA_SIZE) >= len(data) else 0
# #             chunk = bytes([msg_id, seq, is_final, len(part)]) + part
# #             padding = PAYLOAD_SIZE - len(chunk)
# #             chunk += b"\x00" * padding
# #             chunks.append(chunk)
# #         return chunks


# # rf = RF24ReliableInterface()

# # # === Setup TUN Interface ===
# # TUNSETIFF = 0x400454CA
# # IFF_TUN = 0x0001
# # IFF_NO_PI = 0x1000
# # tun = os.open("/dev/net/tun", os.O_RDWR)
# # ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# # fcntl.ioctl(tun, TUNSETIFF, ifr)

# # while True:
# #     # TUN → RF24
# #     rlist, _, _ = select.select([tun], [], [], 0.01)
# #     if tun in rlist:
# #         packet = os.read(tun, 1500)
# #         rf.send(packet)

# #     # RF24 → TUN
# #     data = rf.receive()
# #     if data:
# #         try:
# #             os.write(tun, data)
# #         except Exception as e:
# #             print("[!] TUN write failed:", e)

# #     time.sleep(0.005)


# #!/home/pi/.env/bin/python3

# import fcntl
# import struct
# import select
# import threading
# import queue
# import os
# import time
# import zlib
# import board
# import busio
# import digitalio as dio
# from circuitpython_nrf24l01.rf24 import RF24

# PAYLOAD_SIZE = 32
# CHUNK_DATA_SIZE = 28
# ACK_TIMEOUT = 0.3
# MAX_RETRIES = 5
# IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
# MY_ADDR = b"1Node" if IS_BASE else b"2Node"
# PEER_ADDR = b"2Node" if IS_BASE else b"1Node"


# class RF24ReliableInterface:
#     def __init__(
#         self,
#         tx_addr=MY_ADDR,
#         rx_addr=PEER_ADDR,
#     ):

#         spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

#         tx_ce = dio.DigitalInOut(board.D17)
#         tx_csn = dio.DigitalInOut(board.D8)

#         rx_ce = dio.DigitalInOut(board.D27)
#         rx_csn = dio.DigitalInOut(board.D18)

#         self.tx_radio = RF24(spi, tx_csn, tx_ce)
#         self.rx_radio = RF24(spi, rx_csn, rx_ce)

#         self.tx_radio.pa_level = -12
#         self.rx_radio.pa_level = -12

#         self.tx_radio.payload_size = 32
#         self.rx_radio.payload_size = 32

#         self.tx_radio.channel = 76
#         self.rx_radio.channel = 76

#         # self.tx_radio.open_tx_pipe(tx_addr)
#         self.tx_radio.open_tx_pipe(b"1Node")
#         # self.rx_radio.open_rx_pipe(1, rx_addr)
#         self.rx_radio.open_rx_pipe(1, b"2Node")

#         self.rx_radio.listen = True

#         self.send_queue = queue.Queue()
#         self.recv_queue = queue.Queue()

#         self.running = True
#         self.msg_id = 0
#         self.incoming_buffers = {}

#         self.tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
#         self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)

#         self.tx_thread.start()
#         self.rx_thread.start()

#     def stop(self):
#         self.running = False
#         self.tx_thread.join()
#         self.rx_thread.join()

#     def send(self, data: bytes):
#         self.send_queue.put(data)

#     def receive(self):
#         try:
#             return self.recv_queue.get_nowait()
#         except queue.Empty:
#             return None

#     def _tx_loop(self):
#         while self.running:
#             try:
#                 data = self.send_queue.get(timeout=0.1)
#             except queue.Empty:
#                 continue

#             msg_id = self.msg_id
#             self.msg_id = (self.msg_id + 1) % 256
#             chunks = self._chunk_message(data, msg_id)
#             checksum = zlib.crc32(data).to_bytes(4, "big")

#             for attempt in range(MAX_RETRIES):
#                 for chunk in chunks:
#                     self.tx_radio.listen = False
#                     self.tx_radio.send(chunk)
#                     time.sleep(0.005)

#                 # Wait for ACK
#                 start = time.time()
#                 ack_received = False
#                 self.tx_radio.listen = True
#                 while time.time() - start < ACK_TIMEOUT:
#                     if self.rx_radio.any():
#                         ack = self.rx_radio.recv()
#                         if ack[:3] == b"ACK" and ack[3] == msg_id:
#                             if ack[4:8] == checksum:
#                                 ack_received = True
#                                 break
#                     time.sleep(0.005)
#                 if ack_received:
#                     break
#                 print(f"[!] Resending msg_id {msg_id}")
#             else:
#                 print(f"[X] Failed to send msg_id {msg_id} after retries")

#     def _rx_loop(self):
#         self.rx_radio.listen = True

#         while self.running:
#             if not self.rx_radio.any():
#                 time.sleep(0.01)
#                 continue

#             try:
#                 payload = self.rx_radio.recv()
#             except OSError:
#                 continue

#             if len(payload) < 4:
#                 print("[!] Received incomplete payload")
#                 continue

#             msg_id = payload[0]
#             seq = payload[1]
#             total = payload[2]
#             data = payload[3:]

#             if msg_id not in self.incoming:
#                 self.incoming[msg_id] = [None] * total
#                 self.received[msg_id] = 0
#                 self.checksum[msg_id] = zlib.crc32(data)
#             else:
#                 self.checksum[msg_id] = zlib.crc32(data, self.checksum[msg_id])

#             if self.incoming[msg_id][seq] is None:
#                 self.incoming[msg_id][seq] = data
#                 self.received[msg_id] += 1

#             if self.received[msg_id] == total:
#                 full_msg = b"".join(self.incoming[msg_id])
#                 checksum = self.checksum[msg_id].to_bytes(4, "big")

#                 self.tx_radio.listen = False
#                 self.tx_radio.send(b"ACK" + bytes([msg_id]) + checksum)
#                 self.tx_radio.listen = True

#                 del self.incoming[msg_id]
#                 del self.received[msg_id]
#                 del self.checksum[msg_id]

#                 self.receive_queue.put(full_msg)

#     def _chunk_message(self, data: bytes, msg_id: int):
#         chunks = []
#         for seq, i in enumerate(range(0, len(data), CHUNK_DATA_SIZE)):
#             part = data[i : i + CHUNK_DATA_SIZE]
#             is_final = 1 if (i + CHUNK_DATA_SIZE) >= len(data) else 0
#             chunk = bytes([msg_id, seq, is_final, len(part)]) + part
#             padding = PAYLOAD_SIZE - len(chunk)
#             chunk += b"\x00" * padding
#             chunks.append(chunk)
#         return chunks


# rf = RF24ReliableInterface()

# # === Setup TUN Interface ===
# TUNSETIFF = 0x400454CA
# IFF_TUN = 0x0001
# IFF_NO_PI = 0x1000
# tun = os.open("/dev/net/tun", os.O_RDWR)
# ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# fcntl.ioctl(tun, TUNSETIFF, ifr)

# while True:
#     # TUN → RF24
#     rlist, _, _ = select.select([tun], [], [], 0.01)
#     if tun in rlist:
#         packet = os.read(tun, 1500)
#         rf.send(packet)

#     # RF24 → TUN
#     data = rf.receive()
#     if data:
#         try:
#             os.write(tun, data)
#         except Exception as e:
#             print("[!] TUN write failed:", e)

#     time.sleep(0.005)

#     # tx_ce = dio.DigitalInOut(board.D17)
#     # tx_csn = dio.DigitalInOut(board.D8)

#     # rx_ce = dio.DigitalInOut(board.D27)
#     # rx_csn = dio.DigitalInOut(board.D18)


import board
import digitalio
import busio
from circuitpython_nrf24l01.rf24 import RF24

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
csn = digitalio.DigitalInOut(board.CE1)  # or board.CE0
ce = digitalio.DigitalInOut(board.D25)  # Replace with your CE pin

radio = RF24(spi, csn, ce)
if not radio.begin():
    raise RuntimeError("radio hardware not responding")

print("Radio initialized!")
