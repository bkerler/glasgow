import logging
import asyncio
import math
from nmigen import *

from ...interface.i2c_initiator import I2CInitiatorApplet,I2CInitiatorSubtarget,I2CInitiatorInterface
from ... import *


class FUSB302Error(GlasgowAppletError):
    super(GlasgowAppletError)


class FUSB302Interface:
    def __init__(self, interface, logger, i2c_address):
        self.lower     = interface
        self._i2c_addr = i2c_address
        self._logger   = logger
        self._level    = logging.DEBUG if self._logger.name == __name__ else logging.TRACE

    @staticmethod
    def _check(result):
        if result is None:
            raise FUSB302Error("FUSB302 did not acknowledge command")
        return result

    async def read_reg(self, address):
        self._check(await self.lower.write(self._i2c_addr, [address]))
        data = self._check(await self.lower.read(self._i2c_addr, 1, stop=True))
        self._logger.log(self._level, "FUSB302: reg=%#02x read=<%s>", address, data.hex())
        return data

    async def write_reg(self, address, data):
        data = bytes(data)
        self._logger.log(self._level, "FUSB302: reg=%#02x write=<%s>",
                         address, data.hex())
        self._check(await self.lower.write(self._i2c_addr, [address, len(data), *data], stop=True))


class ControlFUSB302Applet(I2CInitiatorApplet, name="control-fusb302"):
    logger = logging.getLogger(__name__)
    help = "configure FUSB302 USB-PD add-on"
    description = """
    Configure and control the FUSB302-based Glasgow USB-PD add-on
    """

    __pins = ("sda", "scl", "int", "ven", "fault")

    @classmethod
    def add_build_arguments(cls, parser, access):
        # Skip all parent build arguments (port, pins, bitrate)
        # The port_spec is determined dynamically from other options
        # super().add_build_arguments(parser, access)
        # Add the I2CInitiator pin arguments, defaults as per addon board
        access.add_pin_argument(parser, "sda", default=0)
        access.add_pin_argument(parser, "scl", default=1)
        # Add an additional interrupt pin argument, default as per addon board
        access.add_pin_argument(parser, "int", default=2)
        # Add an additional vbus enable pin argument, default as per addon board
        access.add_pin_argument(parser, "ven", default=3)
        # Add an additional vbus fault pin argument, default as per addon board
        access.add_pin_argument(parser, "fault", default=4)
        # Add the bitrate argument, default as per addon board
        parser.add_argument(
            "-b", "--bit-rate", metavar="FREQ", type=int, default=400,
            help="set I2C bit rate to FREQ kHz (default: %(default)s)")
        # Add additional arguments which are specific to the addon board
        parser.add_argument("--sbu-type", choices=('uart', 'i2c', 'trace'), default=None,
            help="set target for SBU1/SBU2")
        parser.add_argument("--usb-type", choices=('uart', 'i2c', 'trace'), default=None,
            help="set target for D+/D-")


    def build(self, target, args):
        # Simple operation only requires port A
        args.port_spec = 'A';
        # Mapping the SBU or USB pins uses port B
        if (args.sbu_type or args.usb_type):
            args.port_spec = 'AB'
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(I2CInitiatorSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            out_fifo=iface.get_out_fifo(),
            in_fifo=iface.get_in_fifo(),
            period_cyc=math.ceil(target.sys_clk_freq / (args.bit_rate * 1000))
        ))
        # TODO: Do something with interrupt pin mapping in the new gateware


    @classmethod
    def add_run_arguments(cls, parser, access):
        # Skip the voltage and pulls run arguments, which we override anyway
        # super().add_run_arguments(parser, access)
        parser.set_defaults(pulls = False)
        def i2c_address(arg):
            return int(arg, 0)
        # Add the I2C address of the controller, defaults to FUSB302B
        parser.add_argument(
            "--i2c-address", type=i2c_address, metavar="ADDR", default=0b0100010,
            help="I2C address of the controller (default: %(default)#02x)")

    async def run(self, device, args):
        # Run port A at 5V
        await device.set_voltage('A', 5.0);
        # Run port B at 3.3V if mapping SBU or USB
        if (args.sbu_type or args.usb_type):
            await device.set_voltage('B', 3.3);
        # Claim the interface(s) needed
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        i2c_iface = I2CInitiatorInterface(iface, self.logger)
        return FUSB302Interface(i2c_iface, self.logger, args.i2c_address)

    @classmethod
    def add_interact_arguments(cls, parser):
        def register(arg):
            return int(arg, 0)
        def hex_bytes(arg):
            return bytes.fromhex(arg)

        p_operation = parser.add_subparsers(dest="operation", metavar="OPERATION", required=True)

        p_read_reg = p_operation.add_parser(
            "read-reg", help="read register")
        p_read_reg.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")

        p_read_all = p_operation.add_parser(
            "read-all", help="read all registers")

        p_write_reg = p_operation.add_parser(
            "write-reg", help="write register")
        p_write_reg.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_write_reg.add_argument(
            "data", metavar="DATA", type=hex_bytes,
            help="data to write, as hex bytes")

    async def interact(self, device, args, fusb302_iface):
        if args.operation == "read-reg":
            print((await fusb302_iface.read_reg(args.address)).hex())

        if args.operation == "read-all":
            for address in range(0x100):
                print("{:02x}: {}"
                      .format(address, (await fusb302_iface.read_reg(address)).hex()))

        if args.operation == "write-reg":
            await fusb302_iface.write_reg(args.address, args.data)
