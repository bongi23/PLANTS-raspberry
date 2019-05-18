from aiohttp import web, http_exceptions, ClientSession
from application_layer import ApplicationLayer

routes = web.RouteTableDef()

app_layer = None

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
    
    resp = await app_layer.send_sensing(microbit_id, sensor_name, sampling_time, min_value, max_value)
    if resp == 0:
        return web.Response()
    elif resp == 1:
        return web.Response(status=404)
    elif resp == 2:
        return web.Response(status=410)


async def start_server(al: ApplicationLayer):
    global app_layer
    app_layer = al
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()



async def send_post(url, url_args=None, params=None, json=None):
    async with ClientSession() as session:
        async with session.post(url.format(*url_args), params=params, json=json) as resp:
            return resp
        

async def send_put(url, url_args=None, params=None, json=None):
    async with ClientSession() as session:
        async with session.put(url.format(*url_args), params=params, json=json) as resp:
            return resp

