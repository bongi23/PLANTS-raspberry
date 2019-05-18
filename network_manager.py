from aiohttp import web, http_exceptions, ClientSession
from serialprotocol import DATA
from serial_manager import SerialManager

routes = web.RouteTableDef()

COMPONENT_ID = 50
SENSING_RESP = 1
SENSING_REQ = 2

serial = None


def check_int(t, name):
    try:
        t = int(t)
    except Exception:
        raise http_exceptions.HttpBadRequest('{0} must be an integer'.format(name))
    if t < 0:
        raise http_exceptions.HttpBadRequest('{0} must be unsigned'.format(name))
    if t.bit_length() > 32:
        raise http_exceptions.HttpBadRequest("{0} can't be more than 32 bit long".format(name))
    

@routes.put('/sensing/{microbit_id}/{sensor_name}')
async def sensing_req(request):
    global serial

    microbit_id = request.match_info['microbit_id']
    check_int(microbit_id, 'microbit_id')
    sampling_time = request.query.get('sampling_time', None)
    if sampling_time is not None:
        check_int(sampling_time,'sampling_time')
    min_value = request.query.get('min_value', None)
    if min_value is not None:
        check_int(min_value, 'min_value')
    max_value = request.query.get('max_value', None)
    if max_value is not None:
        check_int(max_value, 'max_value')

    sensor_name = request.match_info['sensor_name']
    
    resp = await send_sensing(serial, microbit_id, sensor_name, sampling_time, min_value, max_value)
    if resp == 0:
        return web.Response()
    elif resp == 1:
        return web.Response(status=404)
    elif resp == 2:
        return web.Response(status=410)


async def start_server(s: SerialManager):
    global serial
    serial = s
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8081)
    await site.start()



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



async def send_sensing(serial, microbit_id, sensor_name, sample_rate=None, min_val=None, max_val=None):
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
    resp(await serial.recv_send(payload=bytes(msg), full_payload=True))

    return resp.get_data()[0]

