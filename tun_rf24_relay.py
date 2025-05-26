# # #!/home/pi/.env/bin/python3

# # import os
# # import fcntl
# # import struct
# # import time
# # import select
# # import zlib
# # from pyrf24 import RF24, RF24_PA_LOW
# # from construct import Struct, Byte, Bytes, Int16ul, Int32ul
# # from queue import Queue, Empty
# # import threading


# # # === Protocol Definitions ===
# # MAX_RF_PAYLOAD = 32
# # MAX_PACKET_DATA = MAX_RF_PAYLOAD - 8

# # # Each RF packet = [chunk_id:2][total_chunks:2][checksum:4][data:n]
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

# # # === Setup Radio ===
# # radio = RF24(CE_PIN, 0)
# # radio.begin()
# # radio.setPALevel(RF24_PA_LOW)
# # radio.setChannel(76)
# # radio.setPayloadSize(MAX_RF_PAYLOAD)
# # radio.setAutoAck(True)
# # radio.setRetries(5, 15)
# # radio.openWritingPipe(PEER_ADDR)
# # radio.openReadingPipe(1, MY_ADDR)
# # radio.startListening()

# # # === Setup TUN ===
# # TUNSETIFF = 0x400454CA
# # IFF_TUN = 0x0001
# # IFF_NO_PI = 0x1000
# # tun = os.open("/dev/net/tun", os.O_RDWR)
# # ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# # fcntl.ioctl(tun, TUNSETIFF, ifr)


# # tx_queue = Queue(maxsize=100)


# # def tx_worker():
# #     while True:
# #         try:
# #             pkt = tx_queue.get(timeout=1)
# #             send_packet(pkt)
# #         except Empty:
# #             continue
# #         except Exception as e:
# #             print(f"[!] TX Worker error: {e}")


# # tx_thread = threading.Thread(target=tx_worker, daemon=True)
# # tx_thread.start()

# # print("[*] Relay running...")


# # # === Utility ===
# # def chunkify(data, chunk_size):
# #     chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
# #     chunks[-1] += bytes(chunk_size - len(chunks[-1]))  # pad last chunk with null bytes
# #     return chunks


# # def send_with_ack(packet_chunks):
# #     radio.stopListening()
# #     print("Sending", packet_chunks)
# #     for chunk_id, chunk in enumerate(packet_chunks):
# #         for _ in range(5):  # max retries
# #             radio.stopListening()
# #             radio.write(chunk)
# #             time.sleep(0.005)
# #             radio.startListening()
# #             start = time.time()
# #             while time.time() - start < 0.2:  # wait for ack
# #                 if radio.available():
# #                     try:
# #                         ack_payload = radio.read(MAX_RF_PAYLOAD)
# #                         ack = ACKPacket.parse(ack_payload)
# #                         if ack.ack_id == chunk_id:
# #                             break
# #                     except Exception as e:
# #                         print("Error", e)
# #                         continue
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


# # # === Receive Buffer ===
# # recv_chunks = {}
# # recv_total = None


# # def handle_received_packet():
# #     global recv_chunks, recv_total
# #     chunk = radio.read(MAX_RF_PAYLOAD)
# #     pkt = RFPacket.parse(chunk)

# #     # ACK it back
# #     radio.stopListening()
# #     radio.write(ACKPacket.build({"ack_id": pkt.chunk_id}))
# #     radio.startListening()

# #     # Validate
# #     if zlib.crc32(pkt.data) != pkt.checksum:
# #         print("[!] Bad checksum")
# #         return

# #     recv_chunks[pkt.chunk_id] = pkt.data
# #     recv_total = pkt.total_chunks

# #     if recv_total is not None and len(recv_chunks) == recv_total:
# #         full_data = b"".join(recv_chunks[i] for i in sorted(recv_chunks))
# #         try:
# #             os.write(tun, full_data)
# #         except Exception as e:
# #             print(f"[!] Write to TUN failed: {e}")
# #         recv_chunks.clear()
# #         recv_total = None


# # # === Main Loop ===
# # while True:
# #     # TUN → RF24
# #     rlist, _, _ = select.select([tun], [], [], 0.01)
# #     if tun in rlist:
# #         try:
# #             packet = os.read(tun, 1500)
# #             try:
# #                 tx_queue.put_nowait(packet)
# #             except:
# #                 print("[!] Dropped packet due to full TX queue")
# #         except Exception as e:
# #             print(f"[!] Error reading TUN: {e}")

# #     # RF24 → TUN
# #     if radio.available():
# #         try:
# #             handle_received_packet()
# #         except Exception as e:
# #             print(f"[!] Error in radio receive: {e}")

# #     time.sleep(0.001)


# #!/home/pi/.env/bin/python3

# import os
# import fcntl
# import struct
# import time
# import select
# import zlib
# import threading
# from pyrf24 import RF24, RF24_PA_LOW
# from construct import Struct, Byte, Bytes, Int16ul, Int32ul
# from queue import Queue, Empty

# # === Protocol Definitions ===
# MAX_RF_PAYLOAD = 32
# MAX_PACKET_DATA = MAX_RF_PAYLOAD - 8

# RFPacket = Struct(
#     "chunk_id" / Int16ul,
#     "total_chunks" / Int16ul,
#     "checksum" / Int32ul,
#     "data" / Bytes(MAX_PACKET_DATA),
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
#     radio.setPayloadSize(MAX_RF_PAYLOAD)
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
#                             ack_payload = radio.read(MAX_RF_PAYLOAD)
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
#     chunks = chunkify(data, MAX_PACKET_DATA)
#     total = len(chunks)
#     packets = []
#     for i, chunk in enumerate(chunks):
#         checksum = zlib.crc32(chunk)
#         packets.append(
#             RFPacket.build(
#                 {
#                     "chunk_id": i,
#                     "total_chunks": total,
#                     "checksum": checksum,
#                     "data": chunk,
#                 }
#             )
#         )
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
#                 chunk = radio.read(MAX_RF_PAYLOAD)
#             except Exception as e:
#                 print(f"[!] Read error: {e}")
#                 continue

#         try:
#             pkt = RFPacket.parse(chunk)
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


import zlib
import time
import threading
from queue import Queue, Empty
from construct import Struct, Int16ul, Int32ul, Bytes
from RF24 import RF24, RF24_PA_LOW

# Radio setup
radio = RF24(22, 0)
radio.begin()
radio.setPALevel(RF24_PA_LOW)
radio.setDataRate(RF24.BR_1MBPS)
radio.enableDynamicPayloads()
radio.setRetries(5, 15)
radio.setChannel(0x60)
radio.openWritingPipe(b"1Node")
radio.openReadingPipe(1, b"2Node")
radio.startListening()

# Packet structure
RFPacket = Struct(
    "chunk_id" / Int16ul,
    "total_chunks" / Int16ul,
    "checksum" / Int32ul,
    "data" / Bytes(lambda ctx: ctx._.data_size),
)

MAX_PACKET_DATA = 28  # Chunk data size

# Queues
send_queue = Queue()
recv_queue = Queue()

# Lock
radio_lock = threading.Lock()


# Helper: Split into chunks
def chunkify(data: bytes, size: int):
    return [data[i : i + size] for i in range(0, len(data), size)]


# Transmit thread
def sender():
    while True:
        try:
            data = send_queue.get(timeout=1)
        except Empty:
            continue

        chunks = chunkify(data, MAX_PACKET_DATA)
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            checksum = zlib.crc32(chunk)
            packet = RFPacket.build(
                dict(
                    chunk_id=i,
                    total_chunks=total,
                    checksum=checksum,
                    data=chunk,
                    data_size=len(chunk),
                )
            )

            with radio_lock:
                radio.stopListening()
                success = radio.write(packet)
                radio.startListening()

            if not success:
                print(f"[!] Failed to send chunk {i}")
                send_queue.put(data)  # Retry whole data
                break

            time.sleep(0.01)


# Receive thread
def receiver():
    buffers = {}
    timestamps = {}

    while True:
        with radio_lock:
            if not radio.available():
                time.sleep(0.01)
                continue
            length = radio.getDynamicPayloadSize()
            packet_data = radio.read(length)

        try:
            pkt = RFPacket.parse(packet_data, data_size=length - 8)  # 8 = 2+2+4 bytes
        except Exception as e:
            print(f"[!] Parse error: {e}")
            continue

        if zlib.crc32(pkt.data) != pkt.checksum:
            print(f"[!] Bad checksum: id={pkt.chunk_id}")
            continue

        total = pkt.total_chunks
        chunk_id = pkt.chunk_id

        if total not in buffers:
            buffers[total] = [None] * total
            timestamps[total] = time.time()

        buffers[total][chunk_id] = pkt.data

        if all(buffers[total]):
            full_data = b"".join(buffers[total])
            recv_queue.put(full_data)
            del buffers[total]
            del timestamps[total]

        # Timeout cleanup
        for tid in list(timestamps):
            if time.time() - timestamps[tid] > 5:
                print(f"[!] Timeout on message {tid}, dropping")
                del buffers[tid]
                del timestamps[tid]


# Start threads
threading.Thread(target=sender, daemon=True).start()
threading.Thread(target=receiver, daemon=True).start()

# Example usage
if __name__ == "__main__":
    try:
        msg = b"Hello, this is a test message sent over NRF24!"
        send_queue.put(msg)
        print("[>] Message sent")

        while True:
            try:
                received = recv_queue.get(timeout=2)
                print(f"[<] Received: {received}")
            except Empty:
                pass
    except KeyboardInterrupt:
        print("[!] Exiting...")
