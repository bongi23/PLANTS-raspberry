import asyncio
import serial_asyncio
import struct

def microbit_uint_from_bytes(bytes_: bytes):
    return int.from_bytes(bytes_, 'little', signed=False)


def microbit_uint_to_bytes(int_: int, length: int):
    return int_.to_bytes(length, 'little', signed=False)


class SerialManager:
    def __init__(self, device, baudrate=9600):
        self._device = device
        self._baudrate = baudrate
        self._listeners = dict()
        self._is_init = False
        self._queue = asyncio.Queue()

    @property
    def is_init(self):
        return self._is_init

    def listen(self, component_id: int, event_id: int, listener=None,
               full_payload=False):
        if listener:
            self._listeners.setdefault(component_id, {})
            self._listeners[component_id].setdefault(event_id, [])
            self._listeners[component_id][event_id].append((listener,
                                                            full_payload))
        else:
            def decorator(listener):
                self.listen(component_id, event_id, listener, full_payload)
                return listener
            return decorator

    def stop_listening(self, component_id: int, event_id: int, listener):
        if listener:
            components = self._listeners.get(component_id, None)
            if components is not None:
                events = components.get(event_id, None)
                if events is not None:
                    try:
                        events.remove(listener)
                    except ValueError:
                        pass
                if len(events) == 0:
                    components.pop(event_id)
                    if len(components) == 0:
                        self._listeners.pop(component_id)

    def send(self, component_id: int = None, event_id: int = None,
             payload: bytes = None):
        if component_id is not None:
            payload = (microbit_uint_to_bytes(component_id, 1) +
                       microbit_uint_to_bytes(event_id, 1) +
                       microbit_uint_to_bytes(len(payload), 4) +
                       payload)
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            self.event_loop.create_task(self._add_to_send_queue(payload))

    def __enter__(self):
        self.event_loop = asyncio.get_event_loop()
        self.event_loop.run_until_complete(self._init_serial_asyncio())
        self.event_loop.create_task(self._loop())
        self.event_loop.create_task(self._send_loop())
        self._is_init = True

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.event_loop.run_forever()
        self.event_loop.close()
        self._is_init = False

    async def _init_serial_asyncio(self):
        self._reader, self._writer = (
            await serial_asyncio.open_serial_connection(
                url=self._device,
                baudrate=self._baudrate))

    async def _add_to_send_queue(self, payload: bytes):
        await self._queue.put(payload)

    async def recv(self, component_id: int, event_id: int, full_payload=False):
        queue = asyncio.Queue()

        def f(payload):
            queue.put_nowait(payload)
        self.listen(component_id, event_id, f, full_payload)
        payload = await queue.get()
        self.stop_listening(component_id, event_id, f)
        return payload

    async def recv_send(self, component_id: int, event_id: int,
                        full_payload=False, to_send_c_id=None,
                        to_send_e_id=None, payload=None):
        queue = asyncio.Queue()

        def f(p):
            queue.put_nowait(p)
        self.listen(component_id, event_id, f, full_payload)
        self.send(to_send_c_id, to_send_e_id, payload)
        ret = await queue.get()
        self.stop_listening(component_id, event_id, f)
        return ret

    async def _send_loop(self):
        while True:
            payload = await self._queue.get()

            self._writer.write(payload)
            await self._writer.drain()

            self._queue.task_done()

    async def _loop(self):
        while True:
            _component_id = await self._reader.readexactly(1)
            component_id = struct.unpack('=B', _component_id)[0]

            _event_id = await self._reader.readexactly(1)
            event_id = struct.unpack('=B', _event_id)[0]

            _length = await self._reader.readexactly(4)
            length = struct.unpack('=I', _length)[0]

            payload = await self._reader.readexactly(length)

            for listener, full_payload in (self._listeners.get(component_id,
                                                               {})
                                           .get(event_id, [])):
                if full_payload:
                    payload = _component_id + _event_id + payload
                listener(payload)
