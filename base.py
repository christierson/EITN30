import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("10.0.0.1", 5000))
server.listen()

conn, addr = server.accept()
print("Connection from", addr)
data = conn.recv(1024)
print("Received:", data)
conn.sendall(b"Hello Mobile Unit!")
conn.close()
