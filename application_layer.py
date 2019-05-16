from serial_manager import SerialManager
from serialprotocol import DATA

COMPONENT_ID = 50
RESP_SENSING = 1
SENSING_ID = 2


class ApplicationLayer:

    def __init__(self):
        self.__serial = None


    async def send_sensing(self, microbit_id, sample_rate=None, min_val=None, max_val=None):
        #TODO: create message
        msg = DATA(COMPONENT_ID, SENSING_ID)

        resp = await self.__serial.recv_send(payload=msg, full_payload=True)


    def __call__(self, serial: SerialManager):
        self.__serial = serial