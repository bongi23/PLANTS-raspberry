import signal
import sys
import asyncio
from serial_manager import SerialManager
from application_layer import ApplicationLayer
from network_layer_serial_manager import NetworkLayerSerialManager
from serial.serialutil import SerialException
from time import sleep
from network_manager import start_server


DEVICE = '/dev/ttyACM4'
BAUDRATE = 115200


async def main(serial):
    global DEVICE

    args = sys.argv

    if len(sys.argv) > 0:
        DEVICE = sys.argv[0]

    app_layer = ApplicationLayer()
    network_layer = NetworkLayerSerialManager()

    @serial.listen(101, 1)
    def recv1(payload):
        print("NETWORK_LAYER", "DEBUG", payload)

    @serial.listen(100, 2)
    def recv(payload):
        print("APPLICATION:", payload)

    @serial.listen(102, 1)
    def recv2(payload):
        print("APPLICATION_LAYER", "recv:", payload)

    # @serial.listen(120, 1)
    # def recv(payload: bytes):
    #     print("MAC_LAYER", payload)

    network_layer(serial)
    app_layer(serial, network_layer)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

    try:
        with SerialManager(DEVICE, BAUDRATE) as serial:
            asyncio.run(main(serial))
    except Exception as exception:
        print(exception)
