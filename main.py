import signal
import sys
import asyncio
from serial_manager import SerialManager
from application_layer import ApplicationLayer
from network_layer_serial_manager import NetworkLayerSerialManager
from serial.serialutil import SerialException
from time import sleep

DEVICE = '/dev/ttyACM0'
BAUDRATE = 115200


# def main(serial: SerialManager):
def main(serial: SerialManager):
    print('ciao')
    network_layer = NetworkLayerSerialManager()

    @serial.listen(100, 2)
    def _(payload):
        print("APPLICATION:", payload)

    @serial.listen(131, 3)
    def _(payload):
        print("NETWORK_LAYER", "DEBUG:", payload)

    @serial.listen(120, 1)
    def _(payload: bytes):
        print("MAC_LAYER:", payload)

    @serial.listen(120, 2)
    def _(payload: bytes):
        print("MAC_LAYER", "DEBUG:", payload)

    network_layer(serial)

    print('boh')
    with ApplicationLayer() as app_layer:
        print(app_layer)
        app_layer(serial, network_layer)
    print('bah')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

    DEVICE = sys.argv[1] if len(sys.argv) > 1 else DEVICE

    try:
        with SerialManager(DEVICE, BAUDRATE) as serial:
            main(serial)
    except Exception as exception:
        print(exception)
