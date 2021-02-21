import logging
import asyncio
import math
from nmigen import *

from ...interface.i2c_initiator import I2CInitiatorApplet,I2CInitiatorSubtarget,I2CInitiatorInterface
from ... import *


FUSB302_DEVICE_ID   = 0x01
FUSB302_SWITCHES_0  = 0x02
FUSB302_SWITCHES_1  = 0x03
FUSB302_MEASURE     = 0x04
FUSB302_SLICE       = 0x05
FUSB302_CONTROL_0   = 0x06
FUSB302_CONTROL_1   = 0x07
FUSB302_CONTROL_2   = 0x08
FUSB302_CONTROL_3   = 0x09
FUSB302_MASK_1      = 0x0A
FUSB302_POWER       = 0x0B
FUSB302_RESET       = 0x0C
FUSB302_OCP_REG     = 0x0D
FUSB302_MASK_A      = 0x0E
FUSB302_MASK_B      = 0x0F
FUSB302_CONTROL_4   = 0x10
FUSB302_STATUS_0A   = 0x3C
FUSB302_STATUS_1A   = 0x3D
FUSB302_INTERRUPT_A = 0x3E
FUSB302_INTERRUPT_B = 0x3F
FUSB302_STATUS_0    = 0x40
FUSB302_STATUS_1    = 0x41
FUSB302_INTERRUPT   = 0x42
FUSB302_FIFOS       = 0x43


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

    async def block_write(self, addr, data):
        data = bytes(data)

        self._logger.log(self._level, "FUSB302: addr=%s write=<%s>",
                         hex(addr), data.hex())

        # Perform the whole write/read transaction in one chunk, assuming success
        await self.lower._cmd_start()
        await self.lower._cmd_count(2 + len(data))
        await self.lower._cmd_write()
        await self.lower._data_write([(self._i2c_addr << 1) | 0])
        await self.lower._data_write([addr])
        await self.lower._data_write(data)
        await self.lower._cmd_stop()
        
        unacked, = await self.lower._data_read(1)
        acked = len(data) - unacked
        if unacked == 0:
            self._logger.log(self._level, "FUSB302: acked=%d", acked)
        else:
            self._logger.log(self._level, "FUSB302: unacked=%d", unacked)

        return unacked == 0


    async def write(self, addr, data):
        return await self.block_write(addr, [data])


    async def block_read(self, addr, size):
        self._logger.log(self._level, "FUSB302: addr=%s read=%d",
                         hex(addr), size)

        # Perform the whole write/read transaction in one chunk, assuming success
        await self.lower._cmd_start()
        await self.lower._cmd_count(2)
        await self.lower._cmd_write()
        await self.lower._data_write([(self._i2c_addr << 1) | 0])
        await self.lower._data_write([addr])
        await self.lower._cmd_start()
        await self.lower._cmd_count(1)
        await self.lower._cmd_write()
        await self.lower._data_write([(self._i2c_addr << 1) | 1])
        await self.lower._cmd_count(size)
        await self.lower._cmd_read()
        await self.lower._cmd_stop()
        
        # Check the ACK of the slave address and register address write
        unacked, = await self.lower._data_read(1)
        if unacked != 0:
            await self.lower._cmd_stop()
            self._logger.log(self._level, "FUSB302: unacked register address write")
            return None

        # Check the ACK of the slave address and register data read
        unacked, = await self.lower._data_read(1)
        data = await self.lower._data_read(size)
        if unacked == 0:
            self._logger.log(self._level, "FUSB302: acked data=<%s>", data.hex())
            return data
        else:
            self._logger.log(self._level, "FUSB302: unacked data read")
            return None


    async def read(self, addr):
        data = await self._check(self.block_read(addr, 1))
        return data[0]


    async def mask_write(self, addr, mask, value):
        data = await self._check(self.read(addr))
        data &= ~mask
        data |= value
        return await self._check(self.write(addr, data))


    async def set_bits(self, addr, bits):
        return await self._check(self.mask_write(addr, 0, bits))


    async def clear_bits(self, addr, bits):
        return await self._check(self.mask_write(addr, bits, 0))


    async def initialise(self):
        # fusb302_sw_reset()
        await self.set_bits(FUSB302_RESET, 0x01)
        # fusb302_enable_tx_auto_retries(3)
        await self.set_bits(FUSB302_CONTROL_3, (3 << 1) | 1)
        # fusb302_init_interrupt()
        # fusb302_set_power_mode(0xF)
        await self.write(FUSB302_POWER, 0x0F)


    async def set_toggling(self, mode):
        await self.clear_bits(FUSB302_CONTROL_2, 0x01)
        await self.set_bits(FUSB302_MASK_1, 0x21)
        if (mode == 'none'):
            await self.mask_write(FUSB302_CONTROL_2, 0x06, 0x00)
            await self.set_bits(FUSB302_MASK_A, 0x40)
        if (mode == 'drp'):
            await self.mask_write(FUSB302_CONTROL_2, 0x06, 0x02)
            await self.clear_bits(FUSB302_MASK_A, 0x40)
            await self.set_bits(FUSB302_CONTROL_2, 0x01)
        if (mode == 'snk'):
            await self.mask_write(FUSB302_CONTROL_2, 0x06, 0x04)
            await self.clear_bits(FUSB302_MASK_A, 0x40)
            await self.set_bits(FUSB302_CONTROL_2, 0x01)
        if (mode == 'src'):
            await self.mask_write(FUSB302_CONTROL_2, 0x06, 0x06)
            await self.clear_bits(FUSB302_MASK_A, 0x40)
            await self.set_bits(FUSB302_CONTROL_2, 0x01)


class ControlFUSB302Applet(I2CInitiatorApplet, name="control-fusb302"):
    logger = logging.getLogger(__name__)
    help = "configure FUSB302 USB-PD add-on"
    description = """
    Configure and control the FUSB302-based Glasgow USB-PD add-on
    """

    __pins = ("sda", "scl", "int", "ven", "fault")

    __registers = {
        FUSB302_DEVICE_ID:   "DeviceID",
        FUSB302_SWITCHES_0:  "Switches0",
        FUSB302_SWITCHES_1:  "Switches1",
        FUSB302_MEASURE:     "Measure",
        FUSB302_SLICE:       "Slice",
        FUSB302_CONTROL_0:   "Control0",
        FUSB302_CONTROL_1:   "Control1",
        FUSB302_CONTROL_2:   "Control2",
        FUSB302_CONTROL_3:   "Control3",
        FUSB302_MASK_1:      "Mask1",
        FUSB302_POWER:       "Power",
        FUSB302_RESET:       "Reset",
        FUSB302_OCP_REG:     "OCPreg",
        FUSB302_MASK_A:      "MaskA",
        FUSB302_MASK_B:      "MaskB",
        FUSB302_CONTROL_4:   "Control4",
        FUSB302_STATUS_0A:   "Status0A",
        FUSB302_STATUS_1A:   "Status1A",
        FUSB302_INTERRUPT_A: "InterruptA",
        FUSB302_INTERRUPT_B: "InterruptB",
        FUSB302_STATUS_0:    "Status0",
        FUSB302_STATUS_1:    "Status1",
        FUSB302_INTERRUPT:   "Interrupt",
        FUSB302_FIFOS:       "FIFOs",
    }


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
        self.logger.debug("setting port A voltage to 5.0v")
        await device.set_voltage('A', 5.0);
        # Run port B at 3.3V if mapping SBU or USB
        if (args.sbu_type or args.usb_type):
            self.logger.debug("setting port B voltage set to 3.3v")
            await device.set_voltage('B', 3.3);
        # Claim the interface(s) needed
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        i2c_iface = I2CInitiatorInterface(iface, self.logger)
        return FUSB302Interface(i2c_iface, self.logger, args.i2c_address)

    @classmethod
    def add_interact_arguments(cls, parser):
        def register(arg):
            return int(arg, 0)
        def byte(arg):
            return int(arg, 0)
        def hex_bytes(arg):
            return bytes.fromhex(arg)

        p_operation = parser.add_subparsers(dest="operation", metavar="OPERATION", required=True)

        p_read = p_operation.add_parser(
            "read", help="read single register")
        p_read.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")

        p_block_read = p_operation.add_parser(
            "block-read", help="read register block")
        p_block_read.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_block_read.add_argument(
            "size", metavar="SIZE", type=byte,
            help="number of bytes to read")

        p_write = p_operation.add_parser(
            "write", help="write register")
        p_write.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_write.add_argument(
            "data", metavar="DATA", type=byte,
            help="data to write")

        p_block_write = p_operation.add_parser(
            "block-write", help="write register block")
        p_block_write.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_block_write.add_argument(
            "data", metavar="DATA", type=hex_bytes,
            help="data to write, as hex bytes")

        p_mask_write = p_operation.add_parser(
            "mask-write", help="masked write register")
        p_mask_write.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_mask_write.add_argument(
            "mask", metavar="MASK", type=byte,
            help="data mask")
        p_mask_write.add_argument(
            "data", metavar="DATA", type=byte,
            help="data to write")

        p_set_bits = p_operation.add_parser(
            "set-bits", help="set register bits")
        p_set_bits.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_set_bits.add_argument(
            "set-bits", metavar="BITS", type=byte,
            help="data bits to set")

        p_clear_bits = p_operation.add_parser(
            "clear-bits", help="clear register bits")
        p_clear_bits.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_clear_bits.add_argument(
            "clear-bits", metavar="BITS", type=byte,
            help="data bits to clear")

        p_read_all = p_operation.add_parser(
            "read-all", help="read all registers")

        p_sw_reset = p_operation.add_parser(
            "sw-reset", help="reset the controller")

        p_pd_reset = p_operation.add_parser(
            "pd-reset", help="reset the controller PD")

        p_hard_reset = p_operation.add_parser(
            "hard-reset", help="send a HardReset")

        p_init = p_operation.add_parser(
            "init", help="initialise the controller")

        p_set_toggling = p_operation.add_parser(
            "set-toggling", help="set toggling mode")
        p_set_toggling.add_argument("mode", choices=('none', 'src', 'snk', 'drp'),
                                    help="toggle mode")


    async def interact(self, device, args, fusb302_iface):
        if (args.operation == "read"):
            data = await fusb302_iface.read(args.address)
            print(data.hex())

        if (args.operation == "block-read"):
            data = await fusb302_iface.block_read(args.address, args.size)
            print(data.hex())

        if (args.operation == "write"):
            await fusb302_iface.write(args.address, args.data)

        if (args.operation == "block-write"):
            await fusb302_iface.block_write(args.address, args.data)

        if (args.operation == "mask-write"):
            await fusb302_iface.mask_write(args.address, args.mask, args.data)

        if (args.operation == "set-bits"):
            await fusb302_iface.set_bits(args.address, args.bits)

        if (args.operation == "clear-bits"):
            await fusb302_iface.clear_bits(args.address, args.bits)

        if (args.operation == "read-all"):
            for address in self.__registers.keys():
                print("{:11s}[{:02X}]: {:02X}"
                      .format(self.__registers[address], address, (await fusb302_iface.read(address))))

        if (args.operation == "sw-reset"):
            await fusb302_iface.set_bits(FUSB302_RESET, 0x01)

        if (args.operation == "pd-reset"):
            await fusb302_iface.set_bits(FUSB302_RESET, 0x02)

        if (args.operation == "hard-reset"):
            await fusb302_iface.set_bits(FUSB302_CONTROL_3, 0x40)

        if (args.operation == "init"):
            await fusb302_iface.initialise()

        if (args.operation == "set-toggling"):
            await fusb302_iface.set_toggling(args.mode)
