import os
import fcntl
import struct
import time
import select
import zlib
import threading
from pyrf24 import RF24, RF24_PA_LOW
from construct import Struct, Byte, Bytes, Int16ul, Int32ul, Prefixed
import queue


class RF24Interface:
    def __init__(
        self, tx_ce, rx_ce, csn=0, payload_size=32, tx_addr=b"1Node", rx_addr=b"2Node"
    ):
        self.payload_size = payload_size
        self.tx_radio = RF24(tx_ce, csn)
        self.rx_radio = RF24(rx_ce, csn)

        # TX setup
        self.tx_radio.begin()
        self.tx_radio.setPALevel(RF24_PA_LOW)
        self.tx_radio.setChannel(76)
        self.tx_radio.setPayloadSize(payload_size)
        self.tx_radio.openWritingPipe(tx_addr)

        # RX setup
        self.rx_radio.begin()
        self.rx_radio.setPALevel(RF24_PA_LOW)
        self.rx_radio.setChannel(76)
        self.rx_radio.setPayloadSize(payload_size)
        self.rx_radio.openReadingPipe(1, rx_addr)
        self.rx_radio.startListening()

        # Queues
        self.send_queue = queue.Queue()
        self.recv_queue = queue.Queue()

        self.tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)

        self.running = True
        self.tx_thread.start()
        self.rx_thread.start()

    def _tx_loop(self):
        while self.running:
            try:
                data = self.send_queue.get(timeout=0.1)
                self._send_rf24_packet(data)
            except queue.Empty:
                continue

    def _rx_loop(self):
        while self.running:
            if self.rx_radio.available():
                chunk = self.rx_radio.read(self.payload_size)
                self.recv_queue.put(chunk)
            time.sleep(0.005)

    def _send_rf24_packet(self, data: bytes):
        for i in range(0, len(data), self.payload_size):
            chunk = data[i : i + self.payload_size]
            if len(chunk) < self.payload_size:
                chunk += bytes(self.payload_size - len(chunk))
            success = self.tx_radio.write(chunk)
            if not success:
                print("[!] TX failed to write chunk")

    def send(self, data: bytes):
        self.send_queue.put(data)

    def receive(self):
        try:
            return self.recv_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        self.tx_thread.join()
        self.rx_thread.join()
