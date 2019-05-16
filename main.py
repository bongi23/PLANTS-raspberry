#!/usr/bin/python3

import signal
import sys
from serial_manager import SerialManager
from network_layer_serial_manager import NetworkLayerSerialManager
from serial.serialutil import SerialException
from time import sleep


DEVICE = '/dev/ttyACM0'
BAUDRATE = 115200


def main(serial: SerialManager):
    global DEVICE

    args = sys.argv

    if len(sys.argv) > 0:
        DEVICE = sys.argv[0]

    network_layer = NetworkLayerSerialManager()

    @serial.listen(101, 1)
    def recv(payload: bytes):
        print("NETWORK_LAYER", "DEBUG", payload)

    @serial.listen(100, 2)
    def recv(payload: bytes):
        print("APPLICATION:", payload)

    @serial.listen(102, 1)
    def recv(payload: bytes):
        print("APPLICATION_LAYER", "recv:", payload)

    # @serial.listen(120, 1)
    # def recv(payload: bytes):
    #     print("MAC_LAYER", payload)

    network_layer(serial)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

    try:
        with SerialManager(DEVICE, BAUDRATE) as serial:
            main(serial)
    except Exception as exception:
        print(exception)
