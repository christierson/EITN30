#!/home/pi/.env/bin/python

import os
import fcntl
import struct
import time
import select
from pyrf24 import RF24, RF24_PA_LOW

# --- CONFIGURATION ---
IS_BASE = os.getenv("IS_BASE", "false").lower() == "true"
MY_ADDR = b"1Node" if IS_BASE else b"2Node"
PEER_ADDR = b"2Node" if IS_BASE else b"1Node"
CE_PIN = 17 if IS_BASE else 27  # Different CE pins per device
PAYLOAD_SIZE = 32  # Max RF24 payload size

# --- SETUP RADIO ---
radio = RF24(CE_PIN, 0)
radio.begin()
radio.setPALevel(RF24_PA_LOW)
radio.setChannel(76)
radio.setPayloadSize(PAYLOAD_SIZE)
radio.openWritingPipe(PEER_ADDR)
radio.openReadingPipe(1, MY_ADDR)
radio.startListening()

# --- SETUP TUN DEVICE ---
TUNSETIFF = 0x400454CA
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000

tun = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack("16sH", b"tun0", IFF_TUN | IFF_NO_PI)
fcntl.ioctl(tun, TUNSETIFF, ifr)

# Bring up the tun interface in shell beforehand:
# sudo ip addr add 10.0.0.1/24 dev tun0   (on base)
# sudo ip addr add 10.0.0.2/24 dev tun0   (on mobile)
# sudo ip link set tun0 up
# Optional: sudo ip link set tun0 mtu 120

print("[*] Relay running...")

# --- MAIN LOOP ---
while True:
    # 1. Check TUN device for outgoing packets
    rlist, _, _ = select.select([tun], [], [], 0.01)
    if tun in rlist:
        packet = os.read(tun, 1500)
        # Send over RF24 in chunks
        radio.stopListening()
        for i in range(0, len(packet), PAYLOAD_SIZE):
            chunk = packet[i : i + PAYLOAD_SIZE]
            success = radio.write(chunk)
            if not success:
                print("[!] Radio write failed")
        radio.startListening()

    # 2. Poll for incoming RF packets
    if radio.available():
        data = b""
        while radio.available():
            data += radio.read(PAYLOAD_SIZE)

        try:
            os.write(tun, data)
        except:
            print("Invalid package")

    # Sleep a bit to prevent CPU burn
    time.sleep(0.01)
