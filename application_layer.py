from serial_manager import SerialManager
from serialprotocol import DATA
import time
import network_manager
import asyncio
import json
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

    def __call__(self, serial):
        self.__serial = serial

        @serial.listen(COMPONENT_ID, NEW_SAMPLE, full_payload=True)
        def new_sample(payload):
            msg = DATA(COMPONENT_ID, NEW_SAMPLE)
            msg *= 'Isf'
            msg(payload)
            data = msg.get_data()
            o = dict()
            o['microbit'] = data[0]
            o['sensor'] = str(data[1], 'utf-8')
            o['value'] = data[2]
            o['timestamp'] = int(round(time.time() * 1000))
            microbit_id = data[0]
            asyncio.create_task(network_manager.send_post('http://192.168.1.23:8080/sink/{0}', [microbit_id], j=o))

        @serial.listen(COMPONENT_ID, NEW_PLANT, full_payload=True)
        def new_plant(payload):
            msg = DATA(COMPONENT_ID, NEW_PLANT)
            msg *= 'Ias'
            msg(payload)
            data = msg.get_data()
            o = dict()
            o['microbit'] = data[0]
            o['description'] = 'plant'
            o['connected'] = True
            o['sink'] = False
            o['sensors'] = [ str(x,'utf-8') for x in data[1]]
            asyncio.create_task(network_manager.send_put('http://192.168.1.23:8080/sink', j=o))

        @serial.listen(COMPONENT_ID, DISCONNECTED_PLANT, full_payload=True)
        def disconnected_plant(payload):
            msg = DATA(COMPONENT_ID, DISCONNECTED_PLANT)
            msg *= 'I'
            msg(payload)
            data = msg.get_data()
            


