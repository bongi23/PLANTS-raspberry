from serial_manager import SerialManager
from serialprotocol import DATA
import time
import network_manager
import asyncio
import socket

COMPONENT_ID = 50
SENSING_RESP = 1
SENSING_REQ = 2
NEW_SAMPLE = 3
NEW_PLANT = 4
DISCONNECTED_PLANT = 5

'''
    sensing message id 2

    uint32 microbit_id
    string sensor_name
    byte sample_rate
    byte min_val
    byte max_val
    [
        uint32_t sample_rate,
        uint32_t min_val,
        uint32_t max_val
    ]

    response id 1

    byte 
        0 -> fine
        1 -> no route to microbit
        2 -> microbit disconnected

    new_sample id 3

    uint32 microbit_id
    string sensor_name
    float value

    new_plant id 4

    uint32 microbit_id
    char [][] sensors

    disconnected_plant id 5

    uint32 microbit_id

'''

class ApplicationLayer:

    def __init__(self):
        self.__serial = None


    async def send_sensing(self, microbit_id, sensor_name, sample_rate=None, min_val=None, max_val=None):
        #TODO: create message
        msg = DATA(COMPONENT_ID, SENSING_REQ)

        msg += microbit_id
        msg += sensor_name
        if sample_rate is not None:
            msg += ('B', 1)
        else:
            msg += ('B', 0)
        if min_val is not None:
            msg += ('B', 1)
        else:
            msg += ('B', 0)
        if max_val is not None:
            msg += ('B', 1)
        else:
            msg += ('B', 0)
        if sample_rate is not None:
            msg += sample_rate
        if min_val is not None:
            msg += min_val
        if max_val is not None:
            msg += max_val

        resp = DATA(COMPONENT_ID, SENSING_RESP)
        resp *= 'B'
        resp(await self.__serial.recv_send(payload=bytes(msg), full_payload=True))

        return resp.get_data()[0]



    def __call__(self, serial: SerialManager):
        self.__serial = serial

        @serial.listen(COMPONENT_ID, NEW_SAMPLE, full_payload=True)
        def new_sample(payload):
            msg = DATA(COMPONENT_ID, NEW_SAMPLE)
            msg *= 'Isf'
            msg(payload)
            data = msg.get_data()
            o = {}
            o['microbit'] = data[0]
            o['sensor'] = data[1]
            o['value'] = data[2]
            o['timestamp'] = int(round(time.time() * 1000))
            microbit_id = data[0]
            asyncio.create_task(network_manager.send_post('#TODO', [microbit_id], json=o))

        @serial.listen(COMPONENT_ID, NEW_PLANT, full_payload=True)
        def new_plant(payload):
            msg = DATA(COMPONENT_ID, NEW_PLANT)
            msg *= 'Ias'
            msg(payload)
            data = msg.get_data()
            o = {}
            o['microbit'] = data[0]
            o['description'] = 'plant'
            o['connected'] = True
            o['sink'] = False
            o['sensors'] = data[1]
            asyncio.create_task(network_manager.send_put('#TODO', json=o))

        @serial.listen(COMPONENT_ID, DISCONNECTED_PLANT, full_payload=True)
        def disconnected_plant(payload):
            msg = DATA(COMPONENT_ID, DISCONNECTED_PLANT)
            msg *= 'I'
            msg(payload)
            data = msg.get_data()
            


