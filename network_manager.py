from aiohttp import web, http_exceptions, ClientSession
from serialprotocol import DATA
from serial_manager import SerialManager

routes = web.RouteTableDef()

COMPONENT_ID = 50
SENSING_RESP = 1
SENSING_REQ = 3
REMOVE_SENSING_REQ = 4
REMOVE_SENSING_RESP = 2
    




async def send_post(url, url_args=None, params=None, j=None):
    print(j)
    async with ClientSession() as session:
        async with session.post(url.format(*url_args), params=params, json=j) as resp:
            return resp
        

async def send_put(url, url_args=None, params=None, j=None):
    print(j)
    async with ClientSession() as session:
        if url_args is not None:
            async with session.put(url.format(*url_args), params=params, json=j) as resp:
                return resp
        else:
            async with session.put(url, params=params, json=j) as resp:
                return resp

async def send_get(url, url_args=None, params=None, j=None):
    print(j)
    async with ClientSession() as session:
        if url_args is not None:
            async with session.get(url.format(*url_args), params=params, json=j) as resp:
                return resp
        else:
            async with session.get(url, params=params, json=j) as resp:
                return resp        


async def send_sensing(serial, microbit_id, sensor_name, min_val=None, max_val=None):
    #TODO: create message
    msg = DATA(COMPONENT_ID, SENSING_REQ)

    msg += microbit_id
    msg += sensor_name
    if min_val is not None:
        msg += ('B', 1)
    else:
        msg += ('B', 0)
    if max_val is not None:
        msg += ('B', 1)
    else:
        msg += ('B', 0)
    if min_val is not None:
        msg += min_val
    if max_val is not None:
        msg += max_val

    resp = DATA(COMPONENT_ID, SENSING_RESP)
    resp *= 'B'
    resp(await serial.recv_send(COMPONENT_ID, SENSING_RESP, payload=bytes(msg), full_payload=True))

    return resp.get_data()[0]

