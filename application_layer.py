from serial_manager import SerialManager
from serialprotocol import DATA
import time
from network_layer_serial_manager import NetworkLayerSerialManager
import network_manager
import asyncio
import json
import socket
from aiohttp import web, http_exceptions
from typing import Union
import math

#SERVER_URL = '192.168.50.23:8080'
SERVER_URL = '192.168.50.1:8080'
RASPY_URL = '192.168.50.2'

COMPONENT_ID = 50
SENSING_RESP = 1
SENSING_REQ = 2
NEW_SAMPLE = 3
NEW_PLANT = 4
DISCONNECTED_PLANT = 5

'''
    sensing message id 2

    byte resp_id
    uint32 microbit_id
    string sensor_name
    byte start_sampling
        0 -> stop
        1 -> start
    next three are control bytes:
        0 -> the information is not present
        1 -> update the information
        2 -> remove the information
    byte sample_rate
    byte min_val
    byte max_val
    [
        uint32_t sample_rate
        uint32_t min_val,
        uint32_t max_val
    ]

    response id 1

    uint32_t gradient_id
    byte
        0 -> fine
        1 -> no route to microbit
        2 -> microbit disconnected
        3 -> busy doing other work

    new_sample id 3

    uint32 microbit_id
    string sensor_name
    float value

    new_plant id 4

    uint32 microbit_id
    string description
    char [][] sensors

    disconnected_plant id 5

    uint32 microbit_id

'''


def check_int(t, name: str):
    try:
        t = int(t)
    except Exception:
        raise http_exceptions.HttpBadRequest('{0} must be an integer'
                                             .format(name))
    if t.bit_length() > 32:
        raise http_exceptions.HttpBadRequest("{0} can't be more than 32 bit"
                                             .format(name) + "long")


def is_consistent(gradient: dict) -> bool:
    min_val = gradient['min_value']
    max_val = gradient['max_value']
    if min_val is None and max_val is None:
        return False
    if min_val is None:
        return True
    if max_val is None:
        return True
    return min_val < max_val

async def start_server(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, RASPY_URL, 8081)
    await site.start()


class SensorHandle:

    def __init__(self, sensor: str):
        self.__sensor = sensor
        self.__min_val = None
        self.__max_val = None
        self.__sample_time = None
        self.__events = {}

    def __setitem__(self, key: int, value: dict):
        self.__events[key] = value
        if 'min_value' in value:
            new_min = value['min_value']
            self.__min_val = (min(self.__min_val, new_min)
                              if self.__min_val is not None else new_min)
        if 'max_value' in value:
            new_max = value['max_value']
            self.__max_val = (max(self.__max_val, new_max)
                              if self.__max_val is not None else new_max)

        if 'sample_rate' in value:
            self.__sample_time = value['sample_rate']

    def __delitem__(self, key: int):
        event = self.__events.pop(key)
        if 'min_value' in event:
            min_val = event['min_value']
            if self.__min_val == min_val:
                self.__update_min()

        if 'max_value' in event:
            max_val = event['max_value']
            if self.__max_val == max_val:
                self.__update_max()

        if 'sample_rate' in event:
            sample_rate = event['sample_rate']
            if self.__sample_time == sample_rate:
                self.__update_rate()

    def __update_min(self):
        mins = None
        for k in self.__events:
            val = self.__events[k]
            if 'min_value' in val:
                mins = (min(mins, val['min_value'])
                        if mins is not None else val['min_value'])
        self.__min_val = mins

    def __update_max(self):
        maxs = None
        for k in self.__events:
            val = self.__events[k]
            if 'max_value' in val:
                maxs = (max(maxs, val['max_value'])
                        if maxs is not None else val['max_value'])
        self.__max_val = maxs

    def __update_rate(self):
        rate = None
        for k in self.__events:
            val = self.__events[k]
            if 'sample_rate' in val:
                rate = (min(rate, val['sample_rate'])
                        if rate is not None else val['sample_rate'])

    def __call__(self)-> dict:
        start_sampling = 1
        if len(self.__events) == 0:
            start_sampling = 0
        elif len(self.__events) == 1 and -1 in self.__events:
            start_sampling = 0
        return {
            'sensor': self.__sensor,
            'start_sampling': start_sampling,
            'min_value': self.__min_val,
            'max_value': self.__max_val,
            'sample_rate': self.__sample_time
        }


class EventHandlers:

    def __init__(self, microbit_id: int):
        self.__microbit_id = microbit_id
        self.__sensors = {}
        self.__events = {}

    def __setitem__(self, key: Union[int, str], value: dict):
        if type(key) == int:
            self.__set_events(key, value)
            self.__update_sensor(key, value['sensor'], value)
        else:
            self.__update_sample_rate(key, value)

    def __set_events(self, key: int, value: dict):
        self.__events[key] = value

    def __update_sensor(self, id: int, key: str, value: dict):
        sensor = self.__sensors.get(key, None)
        if sensor is None:
            sensor = SensorHandle(key)
            self.__sensors[key] = sensor
        sensor[id] = value

    def __getitem__(self, key: Union[int, str]) -> Union[dict, SensorHandle]:
        if type(key) == int:
            return self.__events[key]
        else:
            return self.__sensors[key]

    def __delitem__(self, key: int):
        event = self.__remove_event(key)
        self.__remove_sensor_event(event['sensor'], key)

    def __remove_event(self, key: int) -> dict:
        event = self.__events.pop(key, None)
        return event

    def __remove_sensor_event(self, name: str, key: int):
        sensor = self.__sensors[name]
        del sensor[key]

    def __update_sample_rate(self, key: str, value: dict):
        sensor = self.__sensors.get(key, None)
        if sensor is None:
            sensor = SensorHandle(key)
            self.__sensors[key] = sensor
        sensor[-1] = value


class ApplicationLayer:

    def __init__(self):
        self.__serial = None
        self.__microbits = {}
        self.__network_layer = None
        self.__value_lock = asyncio.Lock()
        self.__value = 6

    def __enter__(self):
        self.__loop = asyncio.get_event_loop()
        self.__app = web.Application()
        self.__app.router.add_put('/sensing/{microbit_id}/{event_id}',
                                  self.put)
        self.__app.router.add_delete('/sensing/{microbit_id}/{event_id}',
                                     self.delete)
        self.__app.router.add_put('/sensing/{microbit_id}/{sensor_name}/time',
                                  self.update_sample_rate)
        self.__loop.run_until_complete(start_server(self.__app))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__loop.run_forever()
        self.__loop.close()

    async def __handle_sensing_req(self, gradient: dict,
                                   microbit_id: int) -> DATA:
        msg = DATA(COMPONENT_ID, SENSING_REQ)
        async with self.__value_lock:
            val = self.__value
            self.__value += 1
            if self.__value == 256:
                self.__value = 6
        msg += ('B', val)
        msg += [microbit_id, gradient['sensor']]
        if gradient['start_sampling']:
            msg += ('B', 1)
        else:
            msg += ('B', 0)

        if is_consistent(gradient):
            for attr in ['sample_rate', 'min_value', 'max_value']:
                msg += ('B', 0 if gradient[attr] is None else 1)
            for attr in ['sample_rate', 'min_value', 'max_value']:
                if gradient[attr] is not None:
                    msg += gradient[attr]
        else:
            msg += ('B', 0 if gradient['sample_rate'] is None else 1)
            msg += [('B', 2), ('B', 2)]
            if gradient['sample_rate'] is not None:
                msg += gradient['sample_rate']
        resp = DATA(COMPONENT_ID, val)
        resp *= 'B'
        r = 3
        print(msg.get_data())
        while r == 3:
            resp(await self.__serial.recv_send(COMPONENT_ID, val,
                                               payload=bytes(msg),
                                               full_payload=True))
            print(resp.get_data())
            r = resp.get_data()[0]
        return resp

    async def put(self, request: web.Request) -> web.Response:
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
        event_id = int(event_id)
        microbit = self.__microbits.get(microbit_id, None)
        if microbit is None:
            microbit = EventHandlers(microbit_id)
            self.__microbits[microbit_id] = microbit
        o = {'sensor': sensor}
        if min_value is not None:
            o['min_value'] = min_value
        if max_value is not None:
            o['max_value'] = max_value
        print(o)
        microbit[event_id] = o

        gradient = microbit[sensor]()
        resp = await self.__handle_sensing_req(gradient, microbit_id)
        resp = resp.get_data()[0]
        if resp == 0:
            return web.Response()
        elif resp == 1:
            return web.Response(status=404)
        elif resp == 2:
            return web.Response(status=410)

    async def delete(self, request: web.Request) -> web.Response:
        request = request
        microbit_id = request.match_info['microbit_id']
        check_int(microbit_id, 'microbit_id')
        microbit_id = int(microbit_id)
        event_id = request.match_info['event_id']
        event_id = int(event_id)

        microbit = self.__microbits.get(microbit_id, None)
        if microbit is None:
            return web.Response()
        event = microbit[event_id]
        del microbit[event_id]

        gradient = microbit[event['sensor']]()
        resp = await self.__handle_sensing_req(gradient, microbit_id)
        resp = resp.get_data()[0]
        if resp == 0:
            return web.Response()
        elif resp == 1:
            return web.Response(status=404)
        elif resp == 2:
            return web.Response(status=410)

    async def update_sample_rate(self, request: web.Request) -> web.Response:
        microbit_id = request.match_info['microbit_id']
        check_int(microbit_id, 'microbit_id')
        microbit_id = int(microbit_id)
        sensor_name = request.match_info['sensor_name']
        sample_rate = request.query.get('sampling_rate')
        check_int(sample_rate, 'sample_rate')
        sample_rate = int(sample_rate)
        microbit = self.__microbits.get(microbit_id, None)
        if microbit is None:
            microbit = EventHandlers(microbit_id)
            self.__microbits[microbit_id] = microbit

        o = {'sample_rate': sample_rate}
        microbit[sensor_name] = o

        gradient = microbit[sensor_name]()
        resp = await self.__handle_sensing_req(gradient, microbit_id)
        resp = resp.get_data()[0]
        if resp == 0:
            return web.Response()
        elif resp == 1:
            return web.Response(status=404)
        elif resp == 2:
            return web.Response(status=410)

    def __call__(self, serial: SerialManager, nl: NetworkLayerSerialManager):
        self.__serial = serial
        self.__network_layer = nl

        @serial.listen(COMPONENT_ID, NEW_SAMPLE, full_payload=True)
        def _(payload):
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
            asyncio.create_task(network_manager.send_post('http://' +
                                                          SERVER_URL +
                                                          '/sink/{0}',
                                                          [microbit_id], j=o))

        @serial.listen(COMPONENT_ID, NEW_PLANT, full_payload=True)
        def _(payload):
            msg = DATA(COMPONENT_ID, NEW_PLANT)
            msg *= 'Isas'
            msg(payload)
            data = msg.get_data()
            o = dict()
            o['network'] = 'http://192.168.50.2:8081'
            o['microbit'] = data[0]
            o['description'] = str(data[1])
            o['connected'] = True
            o['sink'] = False
            o['sensors'] = [str(x, 'utf-8') for x in data[2]]
            asyncio.create_task(network_manager.send_put('http://' +
                                                         SERVER_URL + '/sink',
                                                         j=o))

        @serial.listen(COMPONENT_ID, DISCONNECTED_PLANT, full_payload=True)
        def _(payload):
            msg = DATA(COMPONENT_ID, DISCONNECTED_PLANT)
            msg *= 'I'
            msg(payload)
            data = msg.get_data()
            o = dict()
            o['microbit'] = data[0]
            o['connected'] = False
            asyncio.create_task(network_manager.send_put('http://' +
                                                         SERVER_URL + '/sink',
                                                         j=o))
