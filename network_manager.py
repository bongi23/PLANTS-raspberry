from aiohttp import web, http_exceptions
from application_layer import ApplicationLayer

routes = web.RouteTableDef()

app_layer = ApplicationLayer()

def check_int(t, name):
    try:
        t = int(t)
    except Exception:
        raise http_exceptions.HttpBadRequest('{0} must be an integer'.format(name))
    if t < 0:
        raise http_exceptions.HttpBadRequest('{0} must be unsigned'.format(name))
    if t.bit_length() > 32:
        raise http_exceptions.HttpBadRequest("{0} can't be more than 32 bit long".format(name))
    

@routes.put('/sensing/{microbit_id:}')
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
    
    resp = await app_layer.send_sensing(microbit_id, sampling_time, min_value, max_value)
    if resp == 0:
        return web.Response()
    elif resp == 1:
        return web.Response(status=404)
    elif resp == 2:
        return web.Response(status=410)




