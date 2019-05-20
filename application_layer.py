from serial_manager import SerialManager
from serialprotocol import DATA
import time
from network_layer_serial_manager import NetworkLayerSerialManager
import network_manager
import asyncio
import json
import socket
from aiohttp import web, http_exceptions

COMPONENT_ID = 50
SENSING_RESP = 1
REMOVE_SENSING_REQ = 4
REMOVE_SENSING_RESP = 2
SENSING_REQ = 3
NEW_SAMPLE = 5
NEW_PLANT = 6
DISCONNECTED_PLANT = 7

'''
    sensing message id 3

    uint32 microbit_id
    uint32 gradient_id
    string sensor_name
    byte min_val
    byte max_val
    [
        uint32_t min_val,
        uint32_t max_val
    ]

    response id 1 or 2

    uint32_t gradient_id
    byte 
        0 -> fine
        1 -> no route to microbit
        2 -> microbit disconnected

    new_sample id 5

    uint32 microbit_id
    string sensor_name
    float value

    new_plant id 6

    uint32 microbit_id
    char [][] sensors

    disconnected_plant id 5

    uint32 microbit_id

'''

def check_int(t, name):
    try:
        t = int(t)
    except Exception:
        raise http_exceptions.HttpBadRequest('{0} must be an integer'.format(name))
    if t < 0:
        raise http_exceptions.HttpBadRequest('{0} must be unsigned'.format(name))
    if t.bit_length() > 32:
        raise http_exceptions.HttpBadRequest("{0} can't be more than 32 bit long".format(name))

routes = web.RouteTableDef()

async def start_server(app):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '10.101.49.39', 8081)
    await site.start()

class EventHandler:

    def __init__(self, microbit_id, sensor=None, min_value=None, max_value=None):
        self.microbit_id = microbit_id
        self.sensor = sensor
        self.min_value = min_value
        self.max_value = max_value

class ApplicationLayer:

    def __init__(self):
        global routes
        self.__serial = None
        self.__events = {}
        self.__network_layer = None

    def __enter__(self):
        self.__loop = asyncio.get_event_loop()
        self.__app = web.Application()
        self.__app.router.add_put('/sensing/{microbit_id}/{event_id}', self.put)
        self.__loop.run_until_complete(start_server(self.__app))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__loop.run_forever()
        self.__loop.close()


    @routes.put('/sensing/{microbit_id}/{event_id}')
    async def put(self, request):
        request = request
        microbit_id = request.match_info['microbit_id']
        check_int(microbit_id, 'microbit_id')
        microbit_id = int(microbit_id)
        min_value = request.query.get('min_value', None)
        if min_value is not None:
            check_int(min_value, 'min_value')
        min_value = int(min_value)
        max_value = request.query.get('max_value', None)
        if max_value is not None:
            check_int(max_value, 'max_value')
        max_value = int(max_value)
        sensor = request.query.get('sensor', None)

        event_id = request.match_info['event_id']
        if len(self.__network_layer.routing_table[microbit_id]) == 0:
            return web.Response(status=404)

        self.__events[event_id] =  EventHandler(microbit_id, sensor, min_value, max_value)

        return web.Response()

    @routes.delete('/sensing/{microbit_id}/{event_id}')
    async def delete(self, request):
        request = request
        microbit_id = request.match_info['microbit_id']
        check_int(microbit_id, 'microbit_id')
        microbit_id = int(microbit_id)
        event_id = request.match_info['event_id']
        event_id = int(event_id)
        self.__events.pop(event_id)
        return web.Response()


    @routes.put('/sensing/{microbit_id}/{sensor_name}/time')
    async def update_sample_rate(self, request):
        microbit_id = request.match_info['microbit_id']
        check_int(microbit_id, 'microbit_id')
        sensor_name = request.match_info['sensor_name']
        sample_rate = request.query.get('sample_rate')
        check_int(sample_rate, 'sample_rate')

        # resp = await self.__serial.recv_send()
        return web.Response()

    def __call__(self, serial: SerialManager, nl: NetworkLayerSerialManager):
        self.__serial = serial
        self.__network_layer = nl
        print('ciao')
 

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
            


