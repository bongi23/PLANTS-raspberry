from serial_manager import (
    SerialManager,
    microbit_uint_from_bytes,
    microbit_uint_to_bytes)
from routingtable import RoutingTable
import asyncio


counter = 0


class NetworkLayerSerialManager:
    COMPONENT_ID = 131
    EVENT_ID = 2

    DD_SERIAL_GET = 0
    DD_SERIAL_PUT = 1
    DD_SERIAL_CLEAR = 2
    DD_SERIAL_INIT = 3
    DD_SERIAL_INIT_ACK = 4

    FALSE = microbit_uint_to_bytes(0, 1)
    TRUE = microbit_uint_to_bytes(1, 1)

    def __init__(self):
        self.routing_table = RoutingTable()
        self.serial_initiated = False

    def _send(self, serial, payload):
        serial.send(self.COMPONENT_ID, self.EVENT_ID, payload)

    def print_routes(self):
        with open('/home/plants/routes', 'w') as routes:
            routes.write(str(self.routing_table))

    def _process_message(self, payload: bytes) -> bytes:
        message_type = microbit_uint_from_bytes(payload[0:1])
        buffer_data = payload[1:]

        if(message_type == self.DD_SERIAL_INIT_ACK):
            self.serial_initiated = True
            return

        if(not self.serial_initiated):
            return

        if(message_type == self.DD_SERIAL_GET):
            # print('RASPBERRY:', 'get', end=' ')
            if(len(buffer_data) != 4):
                return self.FALSE

            destination = microbit_uint_from_bytes(buffer_data)

            # print(destination, end=' = ')
            node_route = self.routing_table[destination]

            if(not node_route):
                return self.FALSE

            result = bytes()
            for node in node_route:
                result += microbit_uint_to_bytes(node, 4)

            # print(node_route)

            return self.TRUE + result

        elif(message_type == self.DD_SERIAL_PUT):
            print('RASPBERRY:', 'put', end=' ')
            if(len(buffer_data) % 4):
                return self.FALSE

            node_route = []
            for i in range(0, int(len(buffer_data)), 4):
                node_route.append(
                    microbit_uint_from_bytes(buffer_data[i:i + 4]))

            try:
                self.routing_table[node_route[-1]] = node_route
            except Exception:
                return self.FALSE

            print('route:', node_route)

            return self.TRUE

        elif(message_type == self.DD_SERIAL_CLEAR):
            global counter
            counter += 1
            print('clear counter', counter)
            self.routing_table.reset()

            return self.TRUE

        else:
            return self.FALSE

    def __call__(self, serial):
        if(not serial.is_init):
            return

        @serial.listen(self.COMPONENT_ID, self.EVENT_ID)
        def _(payload: bytes):
            result = self._process_message(payload)
            self.print_routes()
            if(result):
                self._send(serial, result)

        serial.event_loop.create_task(self._init_connection(serial))

    async def _init_connection(self, serial: SerialManager):
        init = microbit_uint_to_bytes(self.DD_SERIAL_INIT, 1)
        while(not self.serial_initiated):
            self._send(serial, init)
            await asyncio.sleep(0.3)
