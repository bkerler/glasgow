from amaranth.compat import *

from ...support.logging import *
from .. import AccessDemultiplexer, AccessDemultiplexerInterface


class SimulationDemultiplexer(AccessDemultiplexer):
    async def claim_interface(self, applet, mux_interface, args, pull_low=set(), pull_high=set()):
        return SimulationDemultiplexerInterface(self.device, applet, mux_interface)


class SimulationDemultiplexerInterface(AccessDemultiplexerInterface):
    def __init__(self, device, applet, mux_interface):
        super().__init__(device, applet)

        self._in_fifo  = mux_interface.in_fifo
        self._out_fifo = mux_interface.out_fifo


    async def cancel(self):
        pass

    async def reset(self):
        pass

    async def read_task(self,length, data):
        if length is None:
            while (yield self._in_fifo.readable):
                data.append((await self._in_fifo.read()))
        else:
            while len(data) < length:
                self.logger.trace("FIFO: need %d bytes", length - len(data))
                while not (yield self._in_fifo.readable):
                    yield
                data.append((await self._in_fifo.read()))

    async def read(self, length=None):
        data = []
        self.read_task(length, data)
        data = bytes(data)
        self.logger.trace("FIFO: read <%s>", dump_hex(data))
        return data


    async def write(self, data):
        data = bytes(data)
        self.logger.trace("FIFO: write <%s>", dump_hex(data))

        for byte in data:
            while not (yield self._out_fifo.writable):
                yield
            await self._out_fifo.write(byte)

    async def flush(self):
        pass
