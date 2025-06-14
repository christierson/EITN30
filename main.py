from time import sleep
from udp_interface import UdpDevice


def handle_message(data, addr):
    print(f"Received from {addr}: {data.decode()}")


udp = UdpDevice(local_port=5005, remote_port=5005)
udp.start_listening(handle_message)

try:
    i = 0
    while True:
        message = f"Hello {i}".encode()
        udp.send(message)
        sleep(1)
        i += 1
except KeyboardInterrupt:
    udp.stop()
