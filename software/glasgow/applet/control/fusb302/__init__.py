import logging
import asyncio
import math
from nmigen import *

from ...interface.i2c_initiator import I2CInitiatorApplet,I2CInitiatorSubtarget,I2CInitiatorInterface
from ... import *


FUSB302_DEVICEID    = 0x01
FUSB302_SWITCHES0   = 0x02
FUSB302_SWITCHES0_CC2_PU_EN = (1<<7)
FUSB302_SWITCHES0_CC1_PU_EN = (1<<6)
FUSB302_SWITCHES0_VCONN_CC2 = (1<<5)
FUSB302_SWITCHES0_VCONN_CC1 = (1<<4)
FUSB302_SWITCHES0_MEAS_CC2 = (1<<3)
FUSB302_SWITCHES0_MEAS_CC1 = (1<<2)
FUSB302_SWITCHES0_CC2_PD_EN = (1<<1)
FUSB302_SWITCHES0_CC1_PD_EN = (1<<0)
FUSB302_SWITCHES1   = 0x03
FUSB302_SWITCHES1_POWERROLE = (1<<7)
FUSB302_SWITCHES1_SPECREV1 = (1<<6)
FUSB302_SWITCHES1_SPECREV0 = (1<<5)
FUSB302_SWITCHES1_DATAROLE = (1<<4)
FUSB302_SWITCHES1_AUTO_GCRC = (1<<2)
FUSB302_SWITCHES1_TXCC2_EN = (1<<1)
FUSB302_SWITCHES1_TXCC1_EN = (1<<0)
FUSB302_MEASURE     = 0x04
FUSB302_MEASURE_VBUS = (1<<6)
FUSB302_SLICE       = 0x05
FUSB302_CONTROL0    = 0x06
FUSB302_CONTROL0_TX_FLUSH = (1<<6)
FUSB302_CONTROL0_INT_MASK = (1<<5)
FUSB302_CONTROL0_HOST_CUR_MASK = (3<<2)
FUSB302_CONTROL0_HOST_CUR_3A0 = (3<<2)
FUSB302_CONTROL0_HOST_CUR_1A5 = (2<<2)
FUSB302_CONTROL0_HOST_CUR_USB = (1<<2)
FUSB302_CONTROL0_TX_START = (1<<0)
FUSB302_CONTROL1    = 0x07
FUSB302_CONTROL1_ENSOP2DB = (1<<6)
FUSB302_CONTROL1_ENSOP1DB = (1<<5)
FUSB302_CONTROL1_BIST_MODE2 = (1<<4)
FUSB302_CONTROL1_RX_FLUSH = (1<<2)
FUSB302_CONTROL1_ENSOP2 = (1<<1)
FUSB302_CONTROL1_ENSOP1 = (1<<0)
FUSB302_CONTROL2    = 0x08
FUSB302_CONTROL2_MODE = (1<<1)
FUSB302_CONTROL2_MODE_DFP = (0x3)
FUSB302_CONTROL2_MODE_UFP = (0x2)
FUSB302_CONTROL2_MODE_DRP = (0x1)
FUSB302_CONTROL2_MODE_POS = (1)
FUSB302_CONTROL2_TOGGLE = (1<<0)
FUSB302_CONTROL3    = 0x09
FUSB302_CONTROL3_SEND_HARDRESET = (1<<6)
FUSB302_CONTROL3_BIST_TMODE = (1<<5)
FUSB302_CONTROL3_AUTO_HARDRESET = (1<<4)
FUSB302_CONTROL3_AUTO_SOFTRESET = (1<<3)
FUSB302_CONTROL3_N_RETRIES = (1<<1)
FUSB302_CONTROL3_N_RETRIES_POS = (1)
FUSB302_CONTROL3_N_RETRIES_SIZE = (2)
FUSB302_CONTROL3_AUTO_RETRY = (1<<0)
FUSB302_MASK        = 0x0A
FUSB302_MASK_VBUSOK = (1<<7)
FUSB302_MASK_ACTIVITY = (1<<6)
FUSB302_MASK_COMP_CHNG = (1<<5)
FUSB302_MASK_CRC_CHK = (1<<4)
FUSB302_MASK_ALERT = (1<<3)
FUSB302_MASK_WAKE = (1<<2)
FUSB302_MASK_COLLISION = (1<<1)
FUSB302_MASK_BC_LVL = (1<<0)
FUSB302_POWER       = 0x0B
FUSB302_POWER_PWR = (1<<0)
FUSB302_POWER_PWR_LOW = 0x1
FUSB302_POWER_PWR_MEDIUM = 0x3
FUSB302_POWER_PWR_HIGH = 0x7
FUSB302_POWER_PWR_ALL = 0xF
FUSB302_RESET       = 0x0C
FUSB302_RESET_PD_RESET = (1<<1)
FUSB302_RESET_SW_RESET = (1<<0)
FUSB302_OCPREG      = 0x0D
FUSB302_MASKA       = 0x0E
FUSB302_MASKA_OCP_TEMP = (1<<7)
FUSB302_MASKA_TOGDONE = (1<<6)
FUSB302_MASKA_SOFTFAIL = (1<<5)
FUSB302_MASKA_RETRYFAIL = (1<<4)
FUSB302_MASKA_HARDSENT = (1<<3)
FUSB302_MASKA_TX_SUCCESS = (1<<2)
FUSB302_MASKA_SOFTRESET = (1<<1)
FUSB302_MASKA_HARDRESET = (1<<0)
FUSB302_MASKB       = 0x0F
FUSB302_MASKB_GCRCSENT = (1<<0)
FUSB302_CONTROL4    = 0x10
FUSB302_STATUS0A    = 0x3C
FUSB302_STATUS0A_SOFTFAIL = (1<<5)
FUSB302_STATUS0A_RETRYFAIL = (1<<4)
FUSB302_STATUS0A_POWER = (1<<2)
FUSB302_STATUS0A_RX_SOFT_RESET = (1<<1)
FUSB302_STATUS0A_RX_HARD_RESET = (1<<0)
FUSB302_STATUS1A    = 0x3D
FUSB302_STATUS1A_TOGSS = (1<<3)
FUSB302_STATUS1A_TOGSS_RUNNING = 0x0
FUSB302_STATUS1A_TOGSS_SRC1 = 0x1
FUSB302_STATUS1A_TOGSS_SRC2 = 0x2
FUSB302_STATUS1A_TOGSS_SNK1 = 0x5
FUSB302_STATUS1A_TOGSS_SNK2 = 0x6
FUSB302_STATUS1A_TOGSS_AA = 0x7
FUSB302_STATUS1A_TOGSS_POS = (3)
FUSB302_STATUS1A_TOGSS_MASK = (0x7)
FUSB302_STATUS1A_RXSOP2DB = (1<<2)
FUSB302_STATUS1A_RXSOP1DB = (1<<1)
FUSB302_STATUS1A_RXSOP = (1<<0)
FUSB302_INTERRUPTA  = 0x3E
FUSB302_INTERRUPTA_OCP_TEMP = (1<<7)
FUSB302_INTERRUPTA_TOGDONE = (1<<6)
FUSB302_INTERRUPTA_SOFTFAIL = (1<<5)
FUSB302_INTERRUPTA_RETRYFAIL = (1<<4)
FUSB302_INTERRUPTA_HARDSENT = (1<<3)
FUSB302_INTERRUPTA_TX_SUCCESS = (1<<2)
FUSB302_INTERRUPTA_SOFTRESET = (1<<1)
FUSB302_INTERRUPTA_HARDRESET = (1<<0)
FUSB302_INTERRUPTB  = 0x3F
FUSB302_INTERRUPTB_GCRCSENT = (1<<0)
FUSB302_STATUS0     = 0x40
FUSB302_STATUS0_VBUSOK = (1<<7)
FUSB302_STATUS0_ACTIVITY = (1<<6)
FUSB302_STATUS0_COMP = (1<<5)
FUSB302_STATUS0_CRC_CHK = (1<<4)
FUSB302_STATUS0_ALERT = (1<<3)
FUSB302_STATUS0_WAKE = (1<<2)
FUSB302_STATUS0_BC_LVL1 = (1<<1)
FUSB302_STATUS0_BC_LVL0 = (1<<0)
FUSB302_STATUS1     = 0x41
FUSB302_STATUS1_RXSOP2 = (1<<7)
FUSB302_STATUS1_RXSOP1 = (1<<6)
FUSB302_STATUS1_RX_EMPTY = (1<<5)
FUSB302_STATUS1_RX_FULL = (1<<4)
FUSB302_STATUS1_TX_EMPTY = (1<<3)
FUSB302_STATUS1_TX_FULL = (1<<2)
FUSB302_INTERRUPT   = 0x42
FUSB302_INTERRUPT_VBUSOK = (1<<7)
FUSB302_INTERRUPT_ACTIVITY = (1<<6)
FUSB302_INTERRUPT_COMP_CHNG = (1<<5)
FUSB302_INTERRUPT_CRC_CHK = (1<<4)
FUSB302_INTERRUPT_ALERT = (1<<3)
FUSB302_INTERRUPT_WAKE = (1<<2)
FUSB302_INTERRUPT_COLLISION = (1<<1)
FUSB302_INTERRUPT_BC_LVL = (1<<0)
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


    async def auto_goodcrc_enable(self, enable):
        if (enable):
            await self.mask_write(FUSB302_SWITCHES1, 0x64, 0x04)
        else:
            await self.mask_write(FUSB302_SWITCHES1, 0x64, 0x00)


    async def tcpm_init(self):
        # Restore default settings
        await self.set_bits(FUSB302_RESET, 0x01)
        # Read the device ID
        await self.read(FUSB302_DEVICEID)
        # Turn on retries and set number of retries
        await self.set_bits(FUSB302_CONTROL3, (3 << 1) | 1)
        # VBUSOK, BC_LVL, COLLISION, ALERT, CRC_CHK
        await self.write(FUSB302_MASK, 0x64)
        # RETRYFAIL, HARDSENT, TX_SUCCESS, HARDRESET
        await self.write(FUSB302_MASKA, 0xE2)
        # GCRCSENT
        await self.write(FUSB302_MASKB, 0xFE)
        # Interrupt Enable
        await self.clear_bits(FUSB302_CONTROL0, 0x20)
        # RX_FLUSH, ENSOP1DB, ENSOP2DB
        await self.write(FUSB302_CONTROL1, 0x64)
        # Disable GoodCRC
        await self.auto_goodcrc_enable(False)
        # Turn on the power!
        await self.write(FUSB302_POWER, 0x0F)


    async def pd_reset(self):
        # PD_RESET
        await self.write(FUSB302_RESET, 0x02)


    async def tcpm_set_rx_enable(self, enable):
        if (enable == False):
            # Clear CC1/CC2 measure bits
            await self.clear_bits(FUSB302_SWITCHES0, 0x0C)
            # Enable BC_LVL interrupt when disabling PD comm
            await self.clear_bits(FUSB302_MASK, 0x01)
        else:
            await self.mask_write(FUSB302_SWITCHES0, 0x0C, 0x04)
            # Disable BC_LVL interrupt when enabling PD comm
            await self.set_bits(FUSB302_MASK, 0x01)
            # flush rx fifo in case messages have been coming our way
            await self.set_bits(FUSB302_CONTROL1, 0x04)
        await self.auto_goodcrc_enable(enable)


    async def rx_fifo_is_empty(self):
        reg = await self.read(FUSB302_STATUS1)
        return (reg & FUSB302_STATUS1_RX_EMPTY)


    async def tcpm_get_vbus_level(self):
        reg = await self.read(FUSB302_STATUS0);
        return True if (reg & FUSB302_STATUS0_VBUSOK) else False;


    async def setup(self):
        await self.tcpm_init()
        await self.pd_reset()
        await self.tcpm_set_rx_enable(False)
        # await self.tcpm_set_cc('open')
        return await self.read(FUSB302_STATUS0)
            

    async def handle_irq(self):
        irq = await self.read(FUSB302_INTERRUPT)
        irqa = await self.read(FUSB302_INTERRUPTA)
        irqb = await self.read(FUSB302_INTERRUPTB)
        if (irq & FUSB302_INTERRUPT_VBUSOK):
            if (await self.tcpm_get_vbus_level()):
                self._logger.info("IRQ: VBUSOK (VBUS=ON)")
                # self.evt_connect()
                pass
            else:
                self._logger.info("IRQ: VBUSOK (VBUS=OFF)")
                # self.evt_disconnect()
                pass
        if (irqa & FUSB302_INTERRUPTA_HARDRESET):
            self._logger.info("IRQ: HARDRESET")
            # self.evt_disconnect()
            pass
        if (irqb & FUSB302_INTERRUPTB_GCRCSENT):
            self._logger.info("IRQ: GCRCSENT")
            while (self.rx_fifo_is_empty() == 0):
                # self.evt_packet()
                pass


class ControlFUSB302Applet(I2CInitiatorApplet, name="control-fusb302"):
    logger = logging.getLogger(__name__)
    help = "configure FUSB302 USB-PD add-on"
    description = """
    Configure and control the FUSB302-based Glasgow USB-PD add-on
    """

    __pins = ("sda", "scl", "int", "ven", "fault")

    __registers = {
        FUSB302_DEVICEID:   "DeviceID",
        FUSB302_SWITCHES0:  "Switches0",
        FUSB302_SWITCHES1:  "Switches1",
        FUSB302_MEASURE:    "Measure",
        FUSB302_SLICE:      "Slice",
        FUSB302_CONTROL0:   "Control0",
        FUSB302_CONTROL1:   "Control1",
        FUSB302_CONTROL2:   "Control2",
        FUSB302_CONTROL3:   "Control3",
        FUSB302_MASK:       "Mask",
        FUSB302_POWER:      "Power",
        FUSB302_RESET:      "Reset",
        FUSB302_OCPREG:     "OCPreg",
        FUSB302_MASKA:      "MaskA",
        FUSB302_MASKB:      "MaskB",
        FUSB302_CONTROL4:   "Control4",
        FUSB302_STATUS0A:   "Status0A",
        FUSB302_STATUS1A:   "Status1A",
        FUSB302_INTERRUPTA: "InterruptA",
        FUSB302_INTERRUPTB: "InterruptB",
        FUSB302_STATUS0:    "Status0",
        FUSB302_STATUS1:    "Status1",
        FUSB302_INTERRUPT:  "Interrupt",
        FUSB302_FIFOS:      "FIFOs",
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

        p_tcpm_init = p_operation.add_parser(
            "tcpm-init", help="initialise the controller")

        p_setup = p_operation.add_parser(
            "setup", help="setup the controller")

        p_handle_irq = p_operation.add_parser(
            "handle-irq", help="handle interrupts")

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
            await fusb302_iface.pd_reset()

        if (args.operation == "hard-reset"):
            await fusb302_iface.set_bits(FUSB302_CONTROL3, 0x40)

        if (args.operation == "tcpm-init"):
            await fusb302_iface.tcpm_init()

        if (args.operation == "setup"):
            await fusb302_iface.setup()

        if (args.operation == "handle-irq"):
            await fusb302_iface.handle_irq()

        if (args.operation == "set-toggling"):
            await fusb302_iface.set_toggling(args.mode)
