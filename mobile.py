import socket
from device import Device

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("10.0.0.1", 5000))  # connect to base station on port 5000
sock.sendall(b"Hello Base Station!")
response = sock.recv(1024)
print("Received:", response)
sock.close()


class MobileUnit(Device):

    pass
