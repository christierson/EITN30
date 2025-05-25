# #!/home/pi/.env/bin/python

# import os
# import fcntl
# import struct
# import time
# import select
# import zstd
# from pyrf24 import RF24, RF24_PA_LOW


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

# TUNSETIFF = 0x400454CA
# IFF_TUN = 0x0001
# IFF_NO_PI = 0x1000

# tun = os.open("/dev/net/tun", os.O_RDWR)
# ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
# fcntl.ioctl(tun, TUNSETIFF, ifr)

# print("[*] Relay running...")


# def send(data: bytes):
#     data = zstd.compress(data)
#     length = len(data).to_bytes(4, "little")
#     packet = length + data
#     for i in range(0, len(packet), PAYLOAD_SIZE):
#         chunk = packet[i : i + PAYLOAD_SIZE]
#         success = radio.write(chunk)


# while True:
#     # 1. Check TUN device for outgoing packets
#     rlist, _, _ = select.select([tun], [], [], 0.01)
#     if tun in rlist:
#         data = os.read(tun, 1500)
#         data = zstd.compress(data)
#         length = len(data).to_bytes(4, "little")
#         packet = length + data
#         # Send over RF24 in chunks
#         radio.stopListening()
#         for i in range(0, len(packet), PAYLOAD_SIZE):
#             chunk = packet[i : i + PAYLOAD_SIZE]
#             success = radio.write(chunk)
#             if not success:
#                 print("[!] Radio write failed")
#         radio.startListening()

#     # 2. Poll for incoming RF packets
#     if radio.available():
#         data = b""
#         while radio.available():
#             data += radio.read(PAYLOAD_SIZE)
#         try:
#             print("Writing", data)
#             os.write(tun, data)
#         except Exception as e:
#             print(e)

#     # Sleep a bit to prevent CPU burn
#     time.sleep(0.01)


#!/home/pi/.env/bin/python

import os
import fcntl
import struct
import time
import select
from pyrf24 import RF24, RF24_PA_LOW

IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
MY_ADDR = b"1Node" if IS_BASE else b"2Node"
PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
CE_PIN = 17 if IS_BASE else 27
PAYLOAD_SIZE = 32

radio = RF24(CE_PIN, 0)
radio.begin()
radio.setPALevel(RF24_PA_LOW)
radio.setChannel(76)
radio.setPayloadSize(PAYLOAD_SIZE)
radio.openWritingPipe(PEER_ADDR)
radio.openReadingPipe(1, MY_ADDR)
radio.startListening()

# Set up TUN device
TUNSETIFF = 0x400454CA
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
tun = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(tun, TUNSETIFF, ifr)

print("[*] Relay running...")

recv_buffer = b""
expected_len = None


def error_response():
    pass


def send_packet(packet):
    print("sending", packet)
    full_packet = len(packet).to_bytes(4, "little") + packet
    radio.stopListening()
    for i in range(0, len(full_packet), PAYLOAD_SIZE):
        chunk = full_packet[i : i + PAYLOAD_SIZE]
        if not radio.write(chunk):
            print("[!] Radio write failed")
    radio.startListening()


while True:
    # 1. TUN -> RF24
    rlist, _, _ = select.select([tun], [], [], 0.01)
    if tun in rlist:
        packet = os.read(tun, 1500)
        send_packet(packet)

    # 2. RF24 -> TUN
    if radio.available():
        chunk = radio.read(PAYLOAD_SIZE)
        if not chunk:
            break
        try:
            length = int.from_bytes(chunk[:4], "little")
            buffer = chunk[4:]
            while len(buffer) < length:
                buffer += radio.read(PAYLOAD_SIZE)
            print("Received", buffer)
        except Exception as e:
            print("Error", e)
            error_response()

    print("recieved", recv_buffer)
    # while True:
    #     if expected_len is None:
    #         if len(recv_buffer) >= 2:
    #             expected_len = struct.unpack("!H", recv_buffer[:2])[0]
    #             recv_buffer = recv_buffer[2:]
    #         else:
    #             break

    #     if expected_len is not None and len(recv_buffer) >= expected_len:
    #         packet = recv_buffer[:expected_len]
    #         recv_buffer = recv_buffer[expected_len:]
    #         expected_len = None
    #         try:
    #             os.write(tun, packet)
    #         except Exception as e:
    #             print(f"[!] Failed to write to TUN: {e}")
    #     else:
    #         break

    time.sleep(0.005)


recv_buffer = b""

while radio.available():
    recv_buffer += radio.read(PAYLOAD_SIZE)

while len(recv_buffer) >= 2:
    packet_len = struct.unpack("!H", recv_buffer[:2])[0]
    if len(recv_buffer) < 2 + packet_len:
        # Wait for more data
        break
    packet = recv_buffer[2 : 2 + packet_len]
    recv_buffer = recv_buffer[2 + packet_len :]

    try:
        os.write(tun, packet)
    except OSError as e:
        print(f"[!] Failed to write to TUN: {e}", flush=True)
