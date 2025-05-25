# #!/home/pi/.env/bin/python

# import os
# import fcntl
# import struct
# import time
# import select
# from pyrf24 import RF24, RF24_PA_LOW
# from construct import Struct, Byte, Bytes, this

# RF24Frame = Struct("length" / Byte, "data" / Bytes(this.length))

# IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
# MY_ADDR = b"1Node" if IS_BASE else b"2Node"
# PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
# CE_PIN = 17 if IS_BASE else 27
# PAYLOAD_SIZE = 32

# radio = RF24(CE_PIN, 0)
# radio.begin()
# radio.setPALevel(RF24_PA_LOW)
# radio.setChannel(76)
# radio.setPayloadSize(PAYLOAD_SIZE)
# radio.openWritingPipe(PEER_ADDR)
# radio.openReadingPipe(1, MY_ADDR)
# radio.startListening()

# # Set up TUN device
# TUNSETIFF = 0x400454CA
# IFF_TUN = 0x0001
# IFF_NO_PI = 0x1000
# tun = os.open("/dev/net/tun", os.O_RDWR)
# ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# fcntl.ioctl(tun, TUNSETIFF, ifr)

# print("[*] Relay running...")

# recv_buffer = b""
# expected_len = None


# def error_response():
#     pass

# def checksum(data):


# def serialize(data):
#     return RF24Frame.build({"length": len(data), "data": data})


# def deserialize(frame):
#     return RF24Frame.parse(frame)


# def send_packet(data):
#     radio.stopListening()
#     packet = serialize(data)
#     for i in range(0, len(packet), PAYLOAD_SIZE):
#         chunk = packet[i : i + PAYLOAD_SIZE]
#         if not radio.write(chunk):
#             print("[!] Radio write failed")
#     radio.startListening()


# while True:
#     # 1. TUN -> RF24
#     rlist, _, _ = select.select([tun], [], [], 0.01)
#     if tun in rlist:
#         packet = os.read(tun, 1500)
#         send_packet(packet)

#     # 2. RF24 -> TUN
#     if radio.available():
#         chunk = radio.read(PAYLOAD_SIZE)
#         if not chunk:
#             break
#         try:
#             length = int.from_bytes(chunk[:4], "little")
#             print("Receiving message of len", length)
#             buffer = chunk[4:]
#             while len(buffer) < length:
#                 buffer += radio.read(PAYLOAD_SIZE)
#             try:
#                 os.write(tun, buffer)
#             except Exception as e:
#                 print(f"[!] Failed to write to TUN: {e}")
#         except Exception as e:
#             print("Error", e)
#             error_response()

#     time.sleep(0.005)


#!/home/pi/.env/bin/python3

import os
import fcntl
import struct
import time
import select
import zlib
from pyrf24 import RF24, RF24_PA_LOW
from construct import Struct, Byte, Bytes, Int16ul, Int32ul

# === Protocol Definitions ===
MAX_RF_PAYLOAD = 32

# Each RF packet = [chunk_id:2][total_chunks:2][checksum:4][data:n]
RFPacket = Struct(
    "chunk_id" / Int16ul,
    "total_chunks" / Int16ul,
    "checksum" / Int32ul,
    "data" / Bytes(MAX_RF_PAYLOAD - 8),
)

ACKPacket = Struct("ack_id" / Int16ul)

# === Configuration ===
IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
MY_ADDR = b"1Node" if IS_BASE else b"2Node"
PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
CE_PIN = 17 if IS_BASE else 27

# === Setup Radio ===
radio = RF24(CE_PIN, 0)
radio.begin()
radio.setPALevel(RF24_PA_LOW)
radio.setChannel(76)
radio.setPayloadSize(MAX_RF_PAYLOAD)
radio.setAutoAck(True)
radio.setRetries(5, 15)
radio.openWritingPipe(PEER_ADDR)
radio.openReadingPipe(1, MY_ADDR)
radio.startListening()

# === Setup TUN ===
TUNSETIFF = 0x400454CA
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
tun = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(tun, TUNSETIFF, ifr)

print("[*] Relay running...")


# === Utility ===
def chunkify(data, chunk_size):
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


def send_with_ack(packet_chunks):
    radio.stopListening()
    for chunk_id, chunk in enumerate(packet_chunks):
        for _ in range(5):  # max retries
            radio.stopListening()
            radio.write(chunk)
            radio.startListening()
            start = time.time()
            while time.time() - start < 0.2:  # wait for ack
                if radio.available():
                    try:
                        ack_payload = radio.read(MAX_RF_PAYLOAD)
                        ack = ACKPacket.parse(ack_payload)
                        if ack.ack_id == chunk_id:
                            break
                    except Exception:
                        continue
            else:
                print(f"[!] Retry chunk {chunk_id}")
                continue
            break
        else:
            print(f"[X] Failed to send chunk {chunk_id}")
            return False
    return True


def send_packet(data):
    print(len(data))
    chunks = chunkify(data, MAX_RF_PAYLOAD - 8)
    total = len(chunks)
    packets = []
    for i, chunk in enumerate(chunks):
        checksum = zlib.crc32(chunk)
        packets.append(
            RFPacket.build(
                {
                    "chunk_id": i,
                    "total_chunks": total,
                    "checksum": checksum,
                    "data": chunk,
                }
            )
        )
    send_with_ack(packets)


# === Receive Buffer ===
recv_chunks = {}
recv_total = None


def handle_received_packet():
    global recv_chunks, recv_total
    chunk = radio.read(MAX_RF_PAYLOAD)
    pkt = RFPacket.parse(chunk)

    # ACK it back
    radio.stopListening()
    radio.write(ACKPacket.build({"ack_id": pkt.chunk_id}))
    radio.startListening()

    # Validate
    if zlib.crc32(pkt.data) != pkt.checksum:
        print("[!] Bad checksum")
        return

    recv_chunks[pkt.chunk_id] = pkt.data
    recv_total = pkt.total_chunks

    if recv_total is not None and len(recv_chunks) == recv_total:
        full_data = b"".join(recv_chunks[i] for i in sorted(recv_chunks))
        try:
            os.write(tun, full_data)
        except Exception as e:
            print(f"[!] Write to TUN failed: {e}")
        recv_chunks.clear()
        recv_total = None


# === Main Loop ===
while True:
    # TUN → RF24
    rlist, _, _ = select.select([tun], [], [], 0.01)
    if tun in rlist:
        try:
            packet = os.read(tun, 1500)
            send_packet(packet)
        except Exception as e:
            print(f"[!] Error reading TUN: {e}")

    # RF24 → TUN
    if radio.available():
        try:
            handle_received_packet()
        except Exception as e:
            print(f"[!] Error in radio receive: {e}")

    time.sleep(0.001)
