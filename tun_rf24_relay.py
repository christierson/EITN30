# # # #!/home/pi/.env/bin/python3

# # # import os
# # # import fcntl
# # # import struct
# # # import time
# # # import select
# # # import zlib
# # # from pyrf24 import RF24, RF24_PA_LOW
# # # from construct import Struct, Byte, Bytes, Int16ul, Int32ul
# # # from queue import Queue, Empty
# # # import threading


# # # # === Protocol Definitions ===
# # # MAX_RF_PAYLOAD = 32
# # # MAX_PACKET_DATA = MAX_RF_PAYLOAD - 8

# # # # Each RF packet = [chunk_id:2][total_chunks:2][checksum:4][data:n]
# # # RFPacket = Struct(
# # #     "chunk_id" / Int16ul,
# # #     "total_chunks" / Int16ul,
# # #     "checksum" / Int32ul,
# # #     "data" / Bytes(MAX_PACKET_DATA),
# # # )

# # # ACKPacket = Struct("ack_id" / Int16ul)

# # # # === Configuration ===
# # # IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
# # # MY_ADDR = b"1Node" if IS_BASE else b"2Node"
# # # PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
# # # CE_PIN = 17 if IS_BASE else 27

# # # # === Setup Radio ===
# # # radio = RF24(CE_PIN, 0)
# # # radio.begin()
# # # radio.setPALevel(RF24_PA_LOW)
# # # radio.setChannel(76)
# # # radio.setPayloadSize(MAX_RF_PAYLOAD)
# # # radio.setAutoAck(True)
# # # radio.setRetries(5, 15)
# # # radio.openWritingPipe(PEER_ADDR)
# # # radio.openReadingPipe(1, MY_ADDR)
# # # radio.startListening()

# # # # === Setup TUN ===
# # # TUNSETIFF = 0x400454CA
# # # IFF_TUN = 0x0001
# # # IFF_NO_PI = 0x1000
# # # tun = os.open("/dev/net/tun", os.O_RDWR)
# # # ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# # # fcntl.ioctl(tun, TUNSETIFF, ifr)


# # # tx_queue = Queue(maxsize=100)


# # # def tx_worker():
# # #     while True:
# # #         try:
# # #             pkt = tx_queue.get(timeout=1)
# # #             send_packet(pkt)
# # #         except Empty:
# # #             continue
# # #         except Exception as e:
# # #             print(f"[!] TX Worker error: {e}")


# # # tx_thread = threading.Thread(target=tx_worker, daemon=True)
# # # tx_thread.start()

# # # print("[*] Relay running...")


# # # # === Utility ===
# # # def chunkify(data, chunk_size):
# # #     chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
# # #     chunks[-1] += bytes(chunk_size - len(chunks[-1]))  # pad last chunk with null bytes
# # #     return chunks


# # # def send_with_ack(packet_chunks):
# # #     radio.stopListening()
# # #     print("Sending", packet_chunks)
# # #     for chunk_id, chunk in enumerate(packet_chunks):
# # #         for _ in range(5):  # max retries
# # #             radio.stopListening()
# # #             radio.write(chunk)
# # #             time.sleep(0.005)
# # #             radio.startListening()
# # #             start = time.time()
# # #             while time.time() - start < 0.2:  # wait for ack
# # #                 if radio.available():
# # #                     try:
# # #                         ack_payload = radio.read(MAX_RF_PAYLOAD)
# # #                         ack = ACKPacket.parse(ack_payload)
# # #                         if ack.ack_id == chunk_id:
# # #                             break
# # #                     except Exception as e:
# # #                         print("Error", e)
# # #                         continue
# # #             else:
# # #                 print(f"[!] Retry chunk {chunk_id}")
# # #                 continue
# # #             break
# # #         else:
# # #             print(f"[X] Failed to send chunk {chunk_id}")
# # #             return False
# # #     return True


# # # def send_packet(data):
# # #     chunks = chunkify(data, MAX_PACKET_DATA)
# # #     total = len(chunks)
# # #     packets = []
# # #     for i, chunk in enumerate(chunks):
# # #         checksum = zlib.crc32(chunk)
# # #         packets.append(
# # #             RFPacket.build(
# # #                 {
# # #                     "chunk_id": i,
# # #                     "total_chunks": total,
# # #                     "checksum": checksum,
# # #                     "data": chunk,
# # #                 }
# # #             )
# # #         )
# # #     send_with_ack(packets)


# # # # === Receive Buffer ===
# # # recv_chunks = {}
# # # recv_total = None


# # # def handle_received_packet():
# # #     global recv_chunks, recv_total
# # #     chunk = radio.read(MAX_RF_PAYLOAD)
# # #     pkt = RFPacket.parse(chunk)

# # #     # ACK it back
# # #     radio.stopListening()
# # #     radio.write(ACKPacket.build({"ack_id": pkt.chunk_id}))
# # #     radio.startListening()

# # #     # Validate
# # #     if zlib.crc32(pkt.data) != pkt.checksum:
# # #         print("[!] Bad checksum")
# # #         return

# # #     recv_chunks[pkt.chunk_id] = pkt.data
# # #     recv_total = pkt.total_chunks

# # #     if recv_total is not None and len(recv_chunks) == recv_total:
# # #         full_data = b"".join(recv_chunks[i] for i in sorted(recv_chunks))
# # #         try:
# # #             os.write(tun, full_data)
# # #         except Exception as e:
# # #             print(f"[!] Write to TUN failed: {e}")
# # #         recv_chunks.clear()
# # #         recv_total = None


# # # # === Main Loop ===
# # # while True:
# # #     # TUN → RF24
# # #     rlist, _, _ = select.select([tun], [], [], 0.01)
# # #     if tun in rlist:
# # #         try:
# # #             packet = os.read(tun, 1500)
# # #             try:
# # #                 tx_queue.put_nowait(packet)
# # #             except:
# # #                 print("[!] Dropped packet due to full TX queue")
# # #         except Exception as e:
# # #             print(f"[!] Error reading TUN: {e}")

# # #     # RF24 → TUN
# # #     if radio.available():
# # #         try:
# # #             handle_received_packet()
# # #         except Exception as e:
# # #             print(f"[!] Error in radio receive: {e}")

# # #     time.sleep(0.001)


# # #!/home/pi/.env/bin/python3

# # import os
# # import fcntl
# # import struct
# # import time
# # import select
# # import zlib
# # import threading
# # from pyrf24 import RF24, RF24_PA_LOW
# # from construct import Struct, Byte, Bytes, Int16ul, Int32ul
# # from queue import Queue, Empty

# # # === Protocol Definitions ===
# # MAX_RF_PAYLOAD = 32
# # MAX_PACKET_DATA = MAX_RF_PAYLOAD - 8

# # RFPacket = Struct(
# #     "chunk_id" / Int16ul,
# #     "total_chunks" / Int16ul,
# #     "checksum" / Int32ul,
# #     "data" / Bytes(MAX_PACKET_DATA),
# # )

# # ACKPacket = Struct("ack_id" / Int16ul)

# # # === Configuration ===
# # IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
# # MY_ADDR = b"1Node" if IS_BASE else b"2Node"
# # PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
# # CE_PIN = 17 if IS_BASE else 27

# # # === Setup RF24 ===
# # radio = RF24(CE_PIN, 0)
# # radio_lock = threading.Lock()

# # with radio_lock:
# #     radio.begin()
# #     radio.setPALevel(RF24_PA_LOW)
# #     radio.setChannel(76)
# #     radio.setPayloadSize(MAX_RF_PAYLOAD)
# #     radio.setAutoAck(True)
# #     radio.setRetries(5, 15)
# #     radio.openWritingPipe(PEER_ADDR)
# #     radio.openReadingPipe(1, MY_ADDR)
# #     radio.startListening()

# # # === Setup TUN Interface ===
# # TUNSETIFF = 0x400454CA
# # IFF_TUN = 0x0001
# # IFF_NO_PI = 0x1000
# # tun = os.open("/dev/net/tun", os.O_RDWR)
# # ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# # fcntl.ioctl(tun, TUNSETIFF, ifr)

# # # === Shared Queues and Buffers ===
# # tx_queue = Queue(maxsize=100)
# # recv_chunks = {}
# # recv_total = None


# # # === Utility Functions ===
# # def chunkify(data, chunk_size):
# #     chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
# #     chunks[-1] += bytes(chunk_size - len(chunks[-1]))  # pad last chunk
# #     return chunks


# # def send_with_ack(packet_chunks):
# #     with radio_lock:
# #         radio.stopListening()
# #     for chunk_id, chunk in enumerate(packet_chunks):
# #         for _ in range(5):  # max retries
# #             with radio_lock:
# #                 radio.stopListening()
# #                 success = radio.write(chunk)
# #                 radio.startListening()

# #             if not success:
# #                 continue

# #             start = time.time()
# #             while time.time() - start < 0.2:
# #                 with radio_lock:
# #                     if radio.available():
# #                         try:
# #                             ack_payload = radio.read(MAX_RF_PAYLOAD)
# #                         except Exception:
# #                             continue
# #                         try:
# #                             ack = ACKPacket.parse(ack_payload)
# #                             if ack.ack_id == chunk_id:
# #                                 break
# #                         except Exception:
# #                             continue
# #             else:
# #                 print(f"[!] Retry chunk {chunk_id}")
# #                 continue
# #             break
# #         else:
# #             print(f"[X] Failed to send chunk {chunk_id}")
# #             return False
# #     return True


# # def send_packet(data):
# #     chunks = chunkify(data, MAX_PACKET_DATA)
# #     total = len(chunks)
# #     packets = []
# #     for i, chunk in enumerate(chunks):
# #         checksum = zlib.crc32(chunk)
# #         packets.append(
# #             RFPacket.build(
# #                 {
# #                     "chunk_id": i,
# #                     "total_chunks": total,
# #                     "checksum": checksum,
# #                     "data": chunk,
# #                 }
# #             )
# #         )
# #     send_with_ack(packets)


# # # === Thread Workers ===
# # def tx_worker():
# #     while True:
# #         try:
# #             pkt = tx_queue.get(timeout=1)
# #             send_packet(pkt)
# #         except Empty:
# #             continue
# #         except Exception as e:
# #             print(f"[!] TX Worker error: {e}")


# # def rx_worker():
# #     global recv_chunks, recv_total
# #     while True:
# #         with radio_lock:
# #             if not radio.available():
# #                 time.sleep(0.001)
# #                 continue
# #             try:
# #                 chunk = radio.read(MAX_RF_PAYLOAD)
# #             except Exception as e:
# #                 print(f"[!] Read error: {e}")
# #                 continue

# #         try:
# #             pkt = RFPacket.parse(chunk)
# #         except Exception as e:
# #             print(f"[!] Parse error: {e}")
# #             continue

# #         # Send ACK
# #         with radio_lock:
# #             radio.stopListening()
# #             try:
# #                 radio.write(ACKPacket.build({"ack_id": pkt.chunk_id}))
# #             except Exception as e:
# #                 print(f"[!] ACK send error: {e}")
# #             radio.startListening()

# #         # Validate
# #         if zlib.crc32(pkt.data) != pkt.checksum:
# #             print("[!] Bad checksum")
# #             continue

# #         recv_chunks[pkt.chunk_id] = pkt.data
# #         recv_total = pkt.total_chunks

# #         if recv_total is not None and len(recv_chunks) == recv_total:
# #             try:
# #                 full_data = b"".join(recv_chunks[i] for i in sorted(recv_chunks))
# #                 os.write(tun, full_data)
# #             except Exception as e:
# #                 print(f"[!] Write to TUN failed: {e}")
# #             recv_chunks.clear()
# #             recv_total = None


# # def tun_reader():
# #     while True:
# #         rlist, _, _ = select.select([tun], [], [], 1.0)
# #         if tun in rlist:
# #             try:
# #                 packet = os.read(tun, 1500)
# #                 tx_queue.put_nowait(packet)
# #             except Exception as e:
# #                 print(f"[!] Error reading TUN: {e}")


# # # === Start Threads ===
# # tx_thread = threading.Thread(target=tx_worker, daemon=True)
# # rx_thread = threading.Thread(target=rx_worker, daemon=True)
# # tun_thread = threading.Thread(target=tun_reader, daemon=True)

# # tx_thread.start()
# # rx_thread.start()
# # tun_thread.start()

# # print("[*] All threads started. Relay running.")

# # # === Main thread waits forever ===
# # tx_thread.join()
# # rx_thread.join()
# # tun_thread.join()

# #!/home/pi/.env/bin/python3

# import os
# import fcntl
# import struct
# import time
# import select
# import zlib
# import threading
# from pyrf24 import RF24, RF24_PA_LOW
# from construct import Struct, Byte, Bytes, Int16ul, Int32ul, Prefixed
# from queue import Queue, Empty

# # === Protocol Definitions ===
# MAX_RF_PAYLOAD = 32

# # # Dynamic payload support: remove fixed data size from struct
# # RFPacket = Struct(
# #     "chunk_id" / Int16ul,
# #     "total_chunks" / Int16ul,
# #     "checksum" / Int32ul,
# #     "data" / Prefixed(Int16ul, Bytes(lambda ctx: ctx._.data_len)),
# # )

# RFPacket = Struct(
#     "chunk_id" / Int16ul,
#     "total_chunks" / Int16ul,
#     "checksum" / Int32ul,
#     "data" / Prefixed(Int16ul, Bytes(lambda ctx: len(ctx.data))),
# )

# ACKPacket = Struct("ack_id" / Int16ul)

# # === Configuration ===
# IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
# MY_ADDR = b"1Node" if IS_BASE else b"2Node"
# PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
# CE_PIN = 17 if IS_BASE else 27

# # === Setup RF24 ===
# radio = RF24(CE_PIN, 0)
# radio_lock = threading.Lock()

# with radio_lock:
#     radio.begin()
#     radio.setPALevel(RF24_PA_LOW)
#     radio.setChannel(76)
#     radio.enableDynamicPayloads()
#     radio.setAutoAck(True)
#     radio.setRetries(5, 15)
#     radio.openWritingPipe(PEER_ADDR)
#     radio.openReadingPipe(1, MY_ADDR)
#     radio.startListening()

# # === Setup TUN Interface ===
# TUNSETIFF = 0x400454CA
# IFF_TUN = 0x0001
# IFF_NO_PI = 0x1000
# tun = os.open("/dev/net/tun", os.O_RDWR)
# ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# fcntl.ioctl(tun, TUNSETIFF, ifr)

# # === Shared Queues and Buffers ===
# tx_queue = Queue(maxsize=100)
# recv_chunks = {}
# recv_total = None


# # === Utility Functions ===
# # def chunkify(data, chunk_size):
# #     return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
# def chunkify(data, chunk_size):
#     chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
#     chunks[-1] += bytes(chunk_size - len(chunks[-1]))  # pad last chunk
#     return chunks


# def send_with_ack(packet_chunks):
#     with radio_lock:
#         radio.stopListening()
#     for chunk_id, chunk in enumerate(packet_chunks):
#         for _ in range(5):  # max retries
#             with radio_lock:
#                 radio.stopListening()
#                 success = radio.write(chunk)
#                 radio.startListening()

#             if not success:
#                 continue

#             start = time.time()
#             while time.time() - start < 0.2:
#                 with radio_lock:
#                     if radio.available():
#                         try:
#                             ack_payload = radio.read(radio.getDynamicPayloadSize())
#                         except Exception:
#                             continue
#                         try:
#                             ack = ACKPacket.parse(ack_payload)
#                             if ack.ack_id == chunk_id:
#                                 break
#                         except Exception:
#                             continue
#             else:
#                 print(f"[!] Retry chunk {chunk_id}")
#                 continue
#             break
#         else:
#             print(f"[X] Failed to send chunk {chunk_id}")
#             return False
#     return True


# def send_packet(data):
#     chunks = chunkify(data, MAX_RF_PAYLOAD - 10)  # 10 bytes for headers
#     total = len(chunks)
#     packets = []
#     for i, chunk in enumerate(chunks):
#         checksum = zlib.crc32(chunk)
#         packet = RFPacket.build(
#             {"chunk_id": i, "total_chunks": total, "checksum": checksum, "data": chunk}
#         )
#         packets.append(packet)
#     send_with_ack(packets)


# # === Thread Workers ===
# def tx_worker():
#     while True:
#         try:
#             pkt = tx_queue.get(timeout=1)
#             send_packet(pkt)
#         except Empty:
#             continue
#         except Exception as e:
#             print(f"[!] TX Worker error: {e}")


# def rx_worker():
#     global recv_chunks, recv_total
#     while True:
#         with radio_lock:
#             if not radio.available():
#                 time.sleep(0.001)
#                 continue
#             try:
#                 size = radio.getDynamicPayloadSize()
#                 chunk = radio.read(size)
#             except Exception as e:
#                 print(f"[!] Read error: {e}")
#                 continue

#         try:
#             pkt = RFPacket.parse(chunk, data_len=len(chunk) - 10)
#         except Exception as e:
#             print(f"[!] Parse error: {e}")
#             continue

#         # Send ACK
#         with radio_lock:
#             radio.stopListening()
#             try:
#                 radio.write(ACKPacket.build({"ack_id": pkt.chunk_id}))
#             except Exception as e:
#                 print(f"[!] ACK send error: {e}")
#             radio.startListening()

#         # Validate
#         if zlib.crc32(pkt.data) != pkt.checksum:
#             print("[!] Bad checksum")
#             continue

#         recv_chunks[pkt.chunk_id] = pkt.data
#         recv_total = pkt.total_chunks

#         if recv_total is not None and len(recv_chunks) == recv_total:
#             try:
#                 full_data = b"".join(recv_chunks[i] for i in sorted(recv_chunks))
#                 os.write(tun, full_data)
#             except Exception as e:
#                 print(f"[!] Write to TUN failed: {e}")
#             recv_chunks.clear()
#             recv_total = None


# def tun_reader():
#     while True:
#         rlist, _, _ = select.select([tun], [], [], 1.0)
#         if tun in rlist:
#             try:
#                 packet = os.read(tun, 1500)
#                 tx_queue.put_nowait(packet)
#             except Exception as e:
#                 print(f"[!] Error reading TUN: {e}")


# # === Start Threads ===
# tx_thread = threading.Thread(target=tx_worker, daemon=True)
# rx_thread = threading.Thread(target=rx_worker, daemon=True)
# tun_thread = threading.Thread(target=tun_reader, daemon=True)

# tx_thread.start()
# rx_thread.start()
# tun_thread.start()

# print("[*] All threads started. Relay running.")

# # === Main thread waits forever ===
# tx_thread.join()
# rx_thread.join()
# tun_thread.join()

#!/home/pi/.env/bin/python3

import fcntl
import struct
import select
import threading
import queue
import os
import time
import zlib
from pyrf24 import RF24, RF24_PA_LOW


PAYLOAD_SIZE = 32
CHUNK_DATA_SIZE = 28
ACK_TIMEOUT = 0.3
MAX_RETRIES = 5
IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
MY_ADDR = b"1Node" if IS_BASE else b"2Node"
PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
TX_PIN = 17
RX_PIN = 27


class RF24ReliableInterface:
    def __init__(
        self, tx_ce=TX_PIN, rx_ce=RX_PIN, csn=0, tx_addr=MY_ADDR, rx_addr=PEER_ADDR
    ):
        self.tx_radio = RF24(tx_ce, csn)
        self.rx_radio = RF24(rx_ce, csn)
        self.tx_addr = tx_addr
        self.rx_addr = rx_addr

        self.tx_radio.begin()
        self.rx_radio.begin()

        self.tx_radio.setPALevel(RF24_PA_LOW)
        self.rx_radio.setPALevel(RF24_PA_LOW)

        self.tx_radio.setPayloadSize(PAYLOAD_SIZE)
        self.rx_radio.setPayloadSize(PAYLOAD_SIZE)

        self.tx_radio.setChannel(76)
        self.rx_radio.setChannel(76)

        self.tx_radio.openWritingPipe(tx_addr)
        self.rx_radio.openReadingPipe(1, rx_addr)
        self.rx_radio.startListening()

        self.send_queue = queue.Queue()
        self.recv_queue = queue.Queue()

        self.running = True
        self.msg_id = 0
        self.incoming_buffers = {}  # msg_id -> list of chunks

        self.tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)

        self.tx_thread.start()
        self.rx_thread.start()

    def stop(self):
        self.running = False
        self.tx_thread.join()
        self.rx_thread.join()

    def send(self, data: bytes):
        self.send_queue.put(data)

    def receive(self):
        try:
            return self.recv_queue.get_nowait()
        except queue.Empty:
            return None

    def _tx_loop(self):
        while self.running:
            try:
                data = self.send_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            msg_id = self.msg_id
            self.msg_id = (self.msg_id + 1) % 256
            chunks = self._chunk_message(data, msg_id)
            checksum = zlib.crc32(data).to_bytes(4, "big")

            for attempt in range(MAX_RETRIES):
                for chunk in chunks:
                    self.tx_radio.write(chunk)
                    time.sleep(0.005)

                # Wait for ACK
                start = time.time()
                ack_received = False
                while time.time() - start < ACK_TIMEOUT:
                    if self.rx_radio.available():
                        ack = self.rx_radio.read(PAYLOAD_SIZE)
                        if ack[:3] == b"ACK" and ack[3] == msg_id:
                            if ack[4:8] == checksum:
                                ack_received = True
                                break
                    time.sleep(0.005)
                if ack_received:
                    break
                print(f"[!] Resending msg_id {msg_id}")
            else:
                print(f"[X] Failed to send msg_id {msg_id} after retries")

    def _rx_loop(self):
        while self.running:
            if self.rx_radio.available():
                chunk = self.rx_radio.read(PAYLOAD_SIZE)
                if chunk[:3] == b"ACK":
                    continue  # Skip ACKs, they're for TX thread

                msg_id, seq, final, length = chunk[0], chunk[1], chunk[2], chunk[3]
                payload = chunk[4 : 4 + length]

                buffer = self.incoming_buffers.setdefault(msg_id, {})
                buffer[seq] = payload

                if final == 1:
                    # Assemble full message
                    parts = [buffer[i] for i in sorted(buffer.keys())]
                    full_data = b"".join(parts)
                    try:
                        checksum = zlib.crc32(full_data).to_bytes(4, "big")
                        ack = b"ACK" + bytes([msg_id]) + checksum
                        self.tx_radio.write(ack)
                        self.recv_queue.put(full_data)
                    except Exception as e:
                        print(f"[!] Failed to process full message: {e}")
                    del self.incoming_buffers[msg_id]
            time.sleep(0.002)

    def _chunk_message(self, data: bytes, msg_id: int):
        chunks = []
        for seq, i in enumerate(range(0, len(data), CHUNK_DATA_SIZE)):
            part = data[i : i + CHUNK_DATA_SIZE]
            is_final = 1 if (i + CHUNK_DATA_SIZE) >= len(data) else 0
            chunk = bytes([msg_id, seq, is_final, len(part)]) + part
            padding = PAYLOAD_SIZE - len(chunk)
            chunk += b"\x00" * padding
            chunks.append(chunk)
        return chunks


rf = RF24ReliableInterface()

# === Setup TUN Interface ===
TUNSETIFF = 0x400454CA
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
tun = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(tun, TUNSETIFF, ifr)

while True:
    # TUN → RF24
    rlist, _, _ = select.select([tun], [], [], 0.01)
    if tun in rlist:
        packet = os.read(tun, 1500)
        rf.send(packet)

    # RF24 → TUN
    data = rf.receive()
    if data:
        try:
            os.write(tun, data)
        except Exception as e:
            print("[!] TUN write failed:", e)

    time.sleep(0.005)
