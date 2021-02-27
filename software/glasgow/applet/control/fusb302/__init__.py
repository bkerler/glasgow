import logging
import asyncio
import math
import time

from nmigen import *

from ...interface.i2c_initiator import I2CInitiatorApplet,I2CInitiatorSubtarget,I2CInitiatorInterface
from ... import *

# 

# Chip Device ID - 302A or 302B
FUSB302_DEVID_302A = 0x08
FUSB302_DEVID_302B = 0x09

# FUSB302BUCX / FUSB302BMPX
FUSB302_I2C_ADDR_FLAGS = 0x22
# FUSB302B01MPX
FUSB302_I2C_ADDR_B01_FLAGS = 0x23
# FUSB302B10MPX
FUSB302_I2C_ADDR_B10_FLAGS = 0x24
# FUSB302B11MPX
FUSB302_I2C_ADDR_B11_FLAGS = 0x25

TCPC_REG_DEVICE_ID = 0x01

TCPC_REG_SWITCHES0 = 0x02
TCPC_REG_SWITCHES0_CC2_PU_EN = (1<<7)
TCPC_REG_SWITCHES0_CC1_PU_EN = (1<<6)
TCPC_REG_SWITCHES0_VCONN_CC2 = (1<<5)
TCPC_REG_SWITCHES0_VCONN_CC1 = (1<<4)
TCPC_REG_SWITCHES0_MEAS_CC2 = (1<<3)
TCPC_REG_SWITCHES0_MEAS_CC1 = (1<<2)
TCPC_REG_SWITCHES0_CC2_PD_EN = (1<<1)
TCPC_REG_SWITCHES0_CC1_PD_EN = (1<<0)

TCPC_REG_SWITCHES1 = 0x03
TCPC_REG_SWITCHES1_POWERROLE = (1<<7)
TCPC_REG_SWITCHES1_SPECREV1 = (1<<6)
TCPC_REG_SWITCHES1_SPECREV0 = (1<<5)
TCPC_REG_SWITCHES1_DATAROLE = (1<<4)
TCPC_REG_SWITCHES1_AUTO_GCRC = (1<<2)
TCPC_REG_SWITCHES1_TXCC2_EN = (1<<1)
TCPC_REG_SWITCHES1_TXCC1_EN = (1<<0)

TCPC_REG_MEASURE = 0x04
TCPC_REG_MEASURE_MDAC_MASK = 0x3F
TCPC_REG_MEASURE_VBUS = (1<<6)

TCPC_REG_SLICE = 0x05

TCPC_REG_CONTROL0 = 0x06
TCPC_REG_CONTROL0_TX_FLUSH = (1<<6)
TCPC_REG_CONTROL0_INT_MASK = (1<<5)
TCPC_REG_CONTROL0_HOST_CUR_MASK = (3<<2)
TCPC_REG_CONTROL0_HOST_CUR_3A0 = (3<<2)
TCPC_REG_CONTROL0_HOST_CUR_1A5 = (2<<2)
TCPC_REG_CONTROL0_HOST_CUR_USB = (1<<2)
TCPC_REG_CONTROL0_TX_START = (1<<0)

TCPC_REG_CONTROL1 = 0x07
TCPC_REG_CONTROL1_ENSOP2DB = (1<<6)
TCPC_REG_CONTROL1_ENSOP1DB = (1<<5)
TCPC_REG_CONTROL1_BIST_MODE2 = (1<<4)
TCPC_REG_CONTROL1_RX_FLUSH = (1<<2)
TCPC_REG_CONTROL1_ENSOP2 = (1<<1)
TCPC_REG_CONTROL1_ENSOP1 = (1<<0)

TCPC_REG_CONTROL2    = 0x08
TCPC_REG_CONTROL2_MODE = (1<<1)
TCPC_REG_CONTROL2_MODE_DFP = (0x3)
TCPC_REG_CONTROL2_MODE_UFP = (0x2)
TCPC_REG_CONTROL2_MODE_DRP = (0x1)
TCPC_REG_CONTROL2_MODE_POS = (1)
TCPC_REG_CONTROL2_TOGGLE = (1<<0)

TCPC_REG_CONTROL3    = 0x09
TCPC_REG_CONTROL3_SEND_HARDRESET = (1<<6)
TCPC_REG_CONTROL3_BIST_TMODE = (1<<5)
TCPC_REG_CONTROL3_AUTO_HARDRESET = (1<<4)
TCPC_REG_CONTROL3_AUTO_SOFTRESET = (1<<3)
TCPC_REG_CONTROL3_N_RETRIES = (1<<1)
TCPC_REG_CONTROL3_N_RETRIES_POS = (1)
TCPC_REG_CONTROL3_N_RETRIES_SIZE = (2)
TCPC_REG_CONTROL3_AUTO_RETRY = (1<<0)

TCPC_REG_MASK        = 0x0A
TCPC_REG_MASK_VBUSOK = (1<<7)
TCPC_REG_MASK_ACTIVITY = (1<<6)
TCPC_REG_MASK_COMP_CHNG = (1<<5)
TCPC_REG_MASK_CRC_CHK = (1<<4)
TCPC_REG_MASK_ALERT = (1<<3)
TCPC_REG_MASK_WAKE = (1<<2)
TCPC_REG_MASK_COLLISION = (1<<1)
TCPC_REG_MASK_BC_LVL = (1<<0)

TCPC_REG_POWER       = 0x0B
TCPC_REG_POWER_PWR = (1<<0)
TCPC_REG_POWER_PWR_LOW = 0x1
TCPC_REG_POWER_PWR_MEDIUM = 0x3
TCPC_REG_POWER_PWR_HIGH = 0x7
TCPC_REG_POWER_PWR_ALL = 0xF

TCPC_REG_RESET       = 0x0C
TCPC_REG_RESET_PD_RESET = (1<<1)
TCPC_REG_RESET_SW_RESET = (1<<0)

TCPC_REG_OCPREG      = 0x0D

TCPC_REG_MASKA       = 0x0E
TCPC_REG_MASKA_OCP_TEMP = (1<<7)
TCPC_REG_MASKA_TOGDONE = (1<<6)
TCPC_REG_MASKA_SOFTFAIL = (1<<5)
TCPC_REG_MASKA_RETRYFAIL = (1<<4)
TCPC_REG_MASKA_HARDSENT = (1<<3)
TCPC_REG_MASKA_TX_SUCCESS = (1<<2)
TCPC_REG_MASKA_SOFTRESET = (1<<1)
TCPC_REG_MASKA_HARDRESET = (1<<0)

TCPC_REG_MASKB       = 0x0F
TCPC_REG_MASKB_GCRCSENT = (1<<0)

TCPC_REG_CONTROL4    = 0x10

TCPC_REG_STATUS0A    = 0x3C
TCPC_REG_STATUS0A_SOFTFAIL = (1<<5)
TCPC_REG_STATUS0A_RETRYFAIL = (1<<4)
TCPC_REG_STATUS0A_POWER = (1<<2)
TCPC_REG_STATUS0A_RX_SOFT_RESET = (1<<1)
TCPC_REG_STATUS0A_RX_HARD_RESET = (1<<0)

TCPC_REG_STATUS1A    = 0x3D
TCPC_REG_STATUS1A_TOGSS = (1<<3)
TCPC_REG_STATUS1A_TOGSS_RUNNING = 0x0
TCPC_REG_STATUS1A_TOGSS_SRC1 = 0x1
TCPC_REG_STATUS1A_TOGSS_SRC2 = 0x2
TCPC_REG_STATUS1A_TOGSS_SNK1 = 0x5
TCPC_REG_STATUS1A_TOGSS_SNK2 = 0x6
TCPC_REG_STATUS1A_TOGSS_AA = 0x7
TCPC_REG_STATUS1A_TOGSS_POS = (3)
TCPC_REG_STATUS1A_TOGSS_MASK = (0x7)
TCPC_REG_STATUS1A_RXSOP2DB = (1<<2)
TCPC_REG_STATUS1A_RXSOP1DB = (1<<1)
TCPC_REG_STATUS1A_RXSOP = (1<<0)

TCPC_REG_INTERRUPTA  = 0x3E
TCPC_REG_INTERRUPTA_OCP_TEMP = (1<<7)
TCPC_REG_INTERRUPTA_TOGDONE = (1<<6)
TCPC_REG_INTERRUPTA_SOFTFAIL = (1<<5)
TCPC_REG_INTERRUPTA_RETRYFAIL = (1<<4)
TCPC_REG_INTERRUPTA_HARDSENT = (1<<3)
TCPC_REG_INTERRUPTA_TX_SUCCESS = (1<<2)
TCPC_REG_INTERRUPTA_SOFTRESET = (1<<1)
TCPC_REG_INTERRUPTA_HARDRESET = (1<<0)

TCPC_REG_INTERRUPTB  = 0x3F
TCPC_REG_INTERRUPTB_GCRCSENT = (1<<0)

TCPC_REG_STATUS0     = 0x40
TCPC_REG_STATUS0_VBUSOK = (1<<7)
TCPC_REG_STATUS0_ACTIVITY = (1<<6)
TCPC_REG_STATUS0_COMP = (1<<5)
TCPC_REG_STATUS0_CRC_CHK = (1<<4)
TCPC_REG_STATUS0_ALERT = (1<<3)
TCPC_REG_STATUS0_WAKE = (1<<2)
TCPC_REG_STATUS0_BC_LVL1 = (1<<1)
TCPC_REG_STATUS0_BC_LVL0 = (1<<0)

TCPC_REG_STATUS1     = 0x41
TCPC_REG_STATUS1_RXSOP2 = (1<<7)
TCPC_REG_STATUS1_RXSOP1 = (1<<6)
TCPC_REG_STATUS1_RX_EMPTY = (1<<5)
TCPC_REG_STATUS1_RX_FULL = (1<<4)
TCPC_REG_STATUS1_TX_EMPTY = (1<<3)
TCPC_REG_STATUS1_TX_FULL = (1<<2)

TCPC_REG_INTERRUPT   = 0x42
TCPC_REG_INTERRUPT_VBUSOK = (1<<7)
TCPC_REG_INTERRUPT_ACTIVITY = (1<<6)
TCPC_REG_INTERRUPT_COMP_CHNG = (1<<5)
TCPC_REG_INTERRUPT_CRC_CHK = (1<<4)
TCPC_REG_INTERRUPT_ALERT = (1<<3)
TCPC_REG_INTERRUPT_WAKE = (1<<2)
TCPC_REG_INTERRUPT_COLLISION = (1<<1)
TCPC_REG_INTERRUPT_BC_LVL = (1<<0)

TCPC_REG_FIFOS       = 0x43

FUSB302_TKN_TXON = 0xA1
FUSB302_TKN_SYNC1 = 0x12
FUSB302_TKN_SYNC2 = 0x13
FUSB302_TKN_SYNC3 = 0x1B
FUSB302_TKN_RST1 = 0x15
FUSB302_TKN_RST2 = 0x16
FUSB302_TKN_PACKSYM = 0x80
FUSB302_TKN_JAMCRC = 0xFF
FUSB302_TKN_EOP = 0x14
FUSB302_TKN_TXOFF = 0xFE
        
PD_SRC_DEF_VNC = ((1600//42) & 0x3F)
PD_SRC_1_5_VNC = ((1600//42) & 0x3F)
PD_SRC_3_0_VNC = ((2600//42) & 0x3F)
PD_SRC_DEF_RD_THRESH = ((200//42) & 0x3F)
PD_SRC_1_5_RD_THRESH = ((400//42) & 0x3F)
PD_SRC_3_0_RD_THRESH = ((800//42) & 0x3F)

TYPEC_CC_VOLT_OPEN = 0
TYPEC_CC_VOLT_RA = 1
TYPEC_CC_VOLT_RD = 2
TYPEC_CC_VOLT_SNK_DEF = 5
TYPEC_CC_VOLT_SNK_1_5 = 6
TYPEC_CC_VOLT_SNK_3_0 = 7

TYPEC_CC_RA = 0
TYPEC_CC_RP = 1
TYPEC_CC_RD = 2
TYPEC_CC_OPEN = 3

STATE_INVALID = -1
STATE_DISCONNECTED = 0
STATE_CONNECTED = 1
STATE_READY = 2
STATE_DFP_VBUS_ON = 3
STATE_DFP_CONNECTED = 4
STATE_IDLE = 5

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


    def platform_usleep(self, us):
        time.sleep(us/1000000)


    # Bring the FUSB302 out of reset after Hard Reset signaling. This will
    # automatically flush both the Rx and Tx FIFOs.
    async def fusb302_pd_reset(self):
        # PD_RESET
        await self.write(TCPC_REG_RESET, TCPC_REG_RESET_PD_RESET)


    async def fusb302_hard_reset(self):
        await self.set_bits(TCPC_REG_CONTROL3, TCPC_REG_CONTROL3_SEND_HARDRESET)

        
    # Flush our Rx FIFO. To prevent packet framing issues, this function should
    # only be called when Rx is disabled.
    async def fusb302_flush_rx_fifo(self):
        await self.set_bits(TCPC_REG_CONTROL1, TCPC_REG_CONTROL1_RX_FLUSH)


    async def fusb302_flush_tx_fifo(self):
        await self.set_bits(TCPC_REG_CONTROL0, TCPC_REG_CONTROL0_TX_FLUSH);


    async def auto_goodcrc_enable(self, enable):
        if (enable):
            await self.set_bits(TCPC_REG_SWITCHES1, TCPC_REG_SWITCHES1_AUTO_GCRC)
        else:
            await self.clear_bits(TCPC_REG_SWITCHES1, TCPC_REG_SWITCHES1_AUTO_GCRC)


    def _convert_bc_lvl(self, bc_lvl):
        ret = TYPEC_CC_VOLT_OPEN
        if (self._pulling_up):
            if (bc_lvl == 0):
                ret = TYPEC_CC_VOLT_RA
            elif (bc_lvl < 3):
                ret = TYPEC_CC_VOLT_RD
        else:
            if (bc_lvl == 1):
                ret = TYPEC_CC_VOLT_SNK_DEF
            elif (bc_lvl == 2):
                ret = TYPEC_CC_VOLT_SNK_1_5
            elif (bc_lvl == 3):
                ret = TYPEC_CC_VOLT_SNK_3_0
        return ret


    async def _measure_cc_pin_source(self, cc_measure):
        # TBD
        fail


    async def _detect_cc_pin_source_manual(self):
        cc1_lvl = -1
        cc2_lvl = -1
        if (self._vconn_enabled):
            # If VCONN enabled, measure cc_pin that matches polarity
            if (self._cc_polarity):
                cc2_lvl = self._measure_cc_pin_source(TCPC_REG_SWITCHES0_MEAS_CC2)
            else:
                cc1_lvl = self._measure_cc_pin_source(TCPC_REG_SWITCHES0_MEAS_CC1)
        else:
            # If VCONN not enabled, measure both cc1 and cc2
            cc1_lvl = self._measure_cc_pin_source(TCPC_REG_SWITCHES0_MEAS_CC1)
            cc2_lvl = self._measure_cc_pin_source(TCPC_REG_SWITCHES0_MEAS_CC2)
        return (cc1_lvl, cc2_lvl)


    async def _detect_cc_pin_sink(self):

        # Measure CC1 first.
        reg = await self.read(TCPC_REG_SWITCHES0)

        # save original state to be returned to later...
        if (reg & TCPC_REG_SWITCHES0_MEAS_CC1):
            orig_meas_cc1 = 1
        else:
            orig_meas_cc1 = 0
        if (reg & TCPC_REG_SWITCHES0_MEAS_CC2):
            orig_meas_cc2 = 1
        else:
            orig_meas_cc2 = 0

        # Disable CC2 measurement switch, enable CC1 measurement switch
        await self.mask_write(TCPC_REG_SWITCHES0,
                              (TCPC_REG_SWITCHES0_MEAS_CC2|TCPC_REG_SWITCHES0_MEAS_CC1),
                              TCPC_REG_SWITCHES0_MEAS_CC1)

        # CC1 is now being measured by FUSB302.

        # Wait on measurement
        self.platform_usleep(250);

        bc_lvl_cc1 = await self.read(TCPC_REG_STATUS0)
        # mask away unwanted bits
        bc_lvl_cc1 &= (TCPC_REG_STATUS0_BC_LVL0 | TCPC_REG_STATUS0_BC_LVL1)
        
        # Measure CC2 next.
        # Disable CC2 measurement switch, enable CC1 measurement switch
        await self.mask_write(TCPC_REG_SWITCHES0,
                              (TCPC_REG_SWITCHES0_MEAS_CC2|TCPC_REG_SWITCHES0_MEAS_CC1),
                              TCPC_REG_SWITCHES0_MEAS_CC2)

        # CC2 is now being measured by FUSB302.
        # Wait on measurement
        self.platform_usleep(250);

        bc_lvl_cc2 = await self.read(TCPC_REG_STATUS0)
        # mask away unwanted bits
        bc_lvl_cc2 &= (TCPC_REG_STATUS0_BC_LVL0 | TCPC_REG_STATUS0_BC_LVL1)

        cc1 = self._convert_bc_lvl(bc_lvl_cc1)
        cc2 = self._convert_bc_lvl(bc_lvl_cc2)

        # return MEAS_CC1/2 switches to original state
        reg = 0
        if (orig_meas_cc1):
            reg |= TCPC_REG_SWITCHES0_MEAS_CC1
        if (orig_meas_cc2):
            reg |= TCPC_REG_SWITCHES0_MEAS_CC2
        await self.mask_write(TCPC_REG_SWITCHES0,
                              (TCPC_REG_SWITCHES0_MEAS_CC2|TCPC_REG_SWITCHES0_MEAS_CC1),
                              reg)

        return (cc1, cc2)
        
        
    def _get_num_bytes(self, header):
        # TBD
        fail


    async def fusb302_send_message(self, header, data, buf, buf_pos):
        # TBD
        fail


    async def fusb302_tcpm_select_rp_value(self, rp):
        # TBD
        fail


    async def fusb302_tcpm_init(self):
        # set default
        self._cc_polarity = -1

        # set the voltage threshold for no connect detection (vOpen)
        self._mdac_vnc = PD_SRC_DEF_VNC
        # set the voltage threshold for Rd vs Ra detection
        self._mdac_rd = PD_SRC_DEF_RD_THRESH

        self._vconn_enabled = 0

        # Restore default settings
        await self.set_bits(TCPC_REG_RESET, TCPC_REG_RESET_SW_RESET)

        # Read the device ID
        await self.read(TCPC_REG_DEVICE_ID)

        # Turn on retries and set number of retries
        await self.set_bits(TCPC_REG_CONTROL3, (3 << TCPC_REG_CONTROL3_N_RETRIES_POS) | TCPC_REG_CONTROL3_AUTO_RETRY)

        # VBUSOK, BC_LVL, COLLISION, ALERT, CRC_CHK
        await self.clear_bits(TCPC_REG_MASK, (TCPC_REG_MASK_VBUSOK|TCPC_REG_MASK_CRC_CHK|TCPC_REG_MASK_ALERT|
                                             TCPC_REG_MASK_COLLISION|TCPC_REG_MASK_BC_LVL))
        # RETRYFAIL, HARDSENT, TX_SUCCESS, HARDRESET
        await self.clear_bits(TCPC_REG_MASKA, (TCPC_REG_MASKA_RETRYFAIL|TCPC_REG_MASKA_HARDSENT|
                                              TCPC_REG_MASKA_TX_SUCCESS|TCPC_REG_MASKA_HARDRESET))
        # GCRCSENT
        await self.clear_bits(TCPC_REG_MASKB, (TCPC_REG_MASKB_GCRCSENT))
        # Interrupt Enable
        await self.clear_bits(TCPC_REG_CONTROL0, TCPC_REG_CONTROL0_INT_MASK)

        # RX_FLUSH, ENSOP1DB, ENSOP2DB
        await self.write(TCPC_REG_CONTROL1, (TCPC_REG_CONTROL1_ENSOP2DB|TCPC_REG_CONTROL1_ENSOP1DB|TCPC_REG_CONTROL1_RX_FLUSH))

        # Disable GoodCRC
        await self.auto_goodcrc_enable(False)

        # Turn on the power!
        await self.write(TCPC_REG_POWER, TCPC_REG_POWER_PWR_ALL)


    async def fusb302_tcpm_get_cc(self):
        if (self._pulling_up):
            cc1,cc2 = await self._detect_cc_pin_source_manual()
        else:
            cc1,cc2 = await self._detect_cc_pin_sink()
        return (cc1, cc2)


    async def fusb302_tcpm_set_cc(self, pull):
        # NOTE: FUSB302 toggles a single pull-up between CC1 and CC2
        # NOTE: FUSB302 Does not support Ra.

        if (pull == TYPEC_CC_RP):
            # enable the pull-up we know to be necessary
            reg = (TCPC_REG_SWITCHES0_CC1_PU_EN |
                   TCPC_REG_SWITCHES0_CC2_PU_EN)
            if (self._vconn_enabled):
                if (self._cc_polarity):
                    reg |= TCPC_REG_SWITCHES0_VCONN_CC1
                else:
                    reg |= TCPC_REG_SWITCHES0_VCONN_CC2
            await self.mask_write(TCPC_REG_SWITCHES0,
                                  (TCPC_REG_SWITCHES0_CC2_PU_EN |
                                   TCPC_REG_SWITCHES0_CC1_PU_EN |
                                   TCPC_REG_SWITCHES0_CC1_PD_EN |
                                   TCPC_REG_SWITCHES0_CC2_PD_EN |
                                   TCPC_REG_SWITCHES0_VCONN_CC1 |
                                   TCPC_REG_SWITCHES0_VCONN_CC2),
                                  reg)
            self._pulling_up = 1;
        elif (pull == TYPEC_CC_RD):
            # Enable UFP Mode
            # turn off toggle
            await self.clear_bits(TCPC_REG_CONTROL2, TCPC_REG_CONTROL2_TOGGLE)
            # enable pull-downs, disable pullups
            reg = (TCPC_REG_SWITCHES0_CC1_PD_EN |
                   TCPC_REG_SWITCHES0_CC2_PD_EN)
            await self.mask_write(TCPC_REG_SWITCHES0,
                            (TCPC_REG_SWITCHES0_CC2_PU_EN |
                             TCPC_REG_SWITCHES0_CC1_PU_EN |
                             TCPC_REG_SWITCHES0_CC1_PD_EN |
                             TCPC_REG_SWITCHES0_CC2_PD_EN),
                            reg)
            self._pulling_up = 0;
        elif (pull == TYPEC_CC_OPEN):
            # Disable toggling
            await self.clear_bits(TCPC_REG_CONTROL2, TCPC_REG_CONTROL2_TOGGLE)
            # Ensure manual switches are opened
            await self.clear_bits(TCPC_REG_SWITCHES0,
                                  (TCPC_REG_SWITCHES0_CC2_PU_EN |
                                   TCPC_REG_SWITCHES0_CC1_PU_EN |
                                   TCPC_REG_SWITCHES0_CC1_PD_EN |
                                   TCPC_REG_SWITCHES0_CC2_PD_EN))
            self._pulling_up = 0;


    async def fusb302_tcpm_set_polarity(self, polarity):
        reg = 0
        if (self._vconn_enabled):
            # set VCONN switch to be non-CC line
            if (polarity):
                reg |= TCPC_REG_SWITCHES0_VCONN_CC1
            else:
                reg |= TCPC_REG_SWITCHES0_VCONN_CC2
        if (polarity):
            reg |= TCPC_REG_SWITCHES0_MEAS_CC2
        else:
            reg |= TCPC_REG_SWITCHES0_MEAS_CC1
        await self.mask_write(TCPC_REG_SWITCHES0,
                              (TCPC_REG_SWITCHES0_VCONN_CC1|TCPC_REG_SWITCHES0_VCONN_CC2|
                               TCPC_REG_SWITCHES0_MEAS_CC1|TCPC_REG_SWITCHES0_MEAS_CC2),
                              reg)
        reg = 0
        if (polarity):
            reg |= TCPC_REG_SWITCHES1_TXCC2_EN
        else:
            reg |= TCPC_REG_SWITCHES1_TXCC1_EN
        await self.mask_write(TCPC_REG_SWITCHES1,
                              (TCPC_REG_SWITCHES1_TXCC1_EN|TCPC_REG_SWITCHES1_TXCC2_EN),
                              reg)
        self._cc_polarity = polarity


    async def fusb302_tcpm_decode_sop_prime_enable(self, enable):
        # TBD
        fail


    async def fusb302_tcpm_set_vconn(self, enable):
        # TBD
        fail


    async def fusb302_tcpm_set_msg_header(self, power_role, data_role):
        reg = 0
        if (power_role):
            reg |= TCPC_REG_SWITCHES1_POWERROLE
        if (data_role):
            reg |= TCPC_REG_SWITCHES1_DATAROLE
        await self.mask_write(TCPC_REG_SWITCHES1,
                              (TCPC_REG_SWITCHES1_POWERROLE|TCPC_REG_SWITCHES1_DATAROLE),
                              reg)


    async def fusb302_tcpm_set_rx_enable(self, enable):
        if (enable):
            if (self._cc_polarity == 0):
                await self.mask_write(TCPC_REG_SWITCHES0,
                                      (TCPC_REG_SWITCHES0_MEAS_CC2|TCPC_REG_SWITCHES0_MEAS_CC1),
                                      TCPC_REG_SWITCHES0_MEAS_CC1)
            elif (self._cc_polarity == 1):
                await self.mask_write(TCPC_REG_SWITCHES0,
                                      (TCPC_REG_SWITCHES0_MEAS_CC2|TCPC_REG_SWITCHES0_MEAS_CC1),
                                      TCPC_REG_SWITCHES0_MEAS_CC2)
            else:
                # Clear CC1/CC2 measure bits
                await self.clear_bits(TCPC_REG_SWITCHES0, (TCPC_REG_SWITCHES0_MEAS_CC2|TCPC_REG_SWITCHES0_MEAS_CC1))
            # Disable BC_LVL interrupt when enabling PD comm
            await self.set_bits(TCPC_REG_MASK, TCPC_REG_MASK_BC_LVL)
            # flush rx fifo in case messages have been coming our way
            await self.set_bits(TCPC_REG_CONTROL1, TCPC_REG_CONTROL1_RX_FLUSH)
        else:
            # Clear CC1/CC2 measure bits
            await self.clear_bits(TCPC_REG_SWITCHES0, (TCPC_REG_SWITCHES0_MEAS_CC2|TCPC_REG_SWITCHES0_MEAS_CC1))
            # Enable BC_LVL interrupt when disabling PD comm
            await self.clear_bits(TCPC_REG_MASK, TCPC_REG_MASK_BC_LVL)
        # set goodcrc accordingly
        await self.auto_goodcrc_enable(enable)


    async def fusb302_rx_fifo_is_empty(self):
        reg = await self.read(TCPC_REG_STATUS1)
        return (reg & TCPC_REG_STATUS1_RX_EMPTY)


    async def fusb302_tcpm_get_message_raw(self, payload, head):
        # TBD
        fail

        
    async def fusb302_tcpm_transmit(self, type, header, data):
        # TBD
        fail

        
    async def fusb302_tcpm_check_vbus_level(self, level):
        # TBD
        fail

        
    async def fusb302_tcpc_alert(self):
        # TBD
        fail

        
    async def fusb302_tcpm_set_bist_test_data(self):
        # TBD
        fail

        
    async def fusb302_tcpm_set_toggle_mode(self, mode):
        # TBD
        fail

        
    async def fusb302_tcpm_enter_low_power_mode(self):
        # TBD
        fail

        
    async def fusb302_compare_mdac(self, mdac):
        # TBD
        fail

        
    async def tcpc_get_vbus_voltage(self):
        # TBD
        fail

        
    async def tcpm_get_vbus_level(self):
        reg = await self.read(TCPC_REG_STATUS0);
        return True if (reg & TCPC_REG_STATUS0_VBUSOK) else False;


    async def setup(self):
        await self.fusb302_tcpm_init()
        await self.fusb302_pd_reset()
        await self.fusb302_tcpm_set_rx_enable(0)
        await self.fusb302_tcpm_set_cc(TYPEC_CC_OPEN)
        data = await self.read(TCPC_REG_STATUS0)
        self._logger.info("STATUS0: %02X", data)
            

    async def vbus_off(self):
        # TBD
        pass
    

    async def evt_disconnect(self):
        await self.vbus_off()
        await self.fusb302_pd_reset()
        await self.fusb302_tcpm_set_rx_enable(0)
        await self.fusb302_tcpm_set_cc(TYPEC_CC_RD);
        self._state = STATE_DISCONNECTED
        self._logger.info("S: DISCONNECTED")

        
    async def evt_connect(self):
        cc1,cc2 = await self.fusb302_tcpm_get_cc()
        self._logger.info("CC: cc1=%d cc2=%d", cc1, cc2)
        await self.fusb302_pd_reset()
        await self.fusb302_tcpm_set_msg_header(0, 0); # Sink
        if (cc1 > cc2):
            await self.fusb302_tcpm_set_polarity(0);
            self._logger.info("Polarity: CC1 (normal)")
        else:
            await self.fusb302_tcpm_set_polarity(1);
            self._logger.info("Polarity: CC2 (flipped)")
        await self.fusb302_tcpm_set_rx_enable(1)
        self._state = STATE_CONNECTED
        self._logger.info("S: CONNECTED")

        
    async def evt_packet(self):
        # TBD
        fail

        
    async def handle_irq(self):
        irq = await self.read(TCPC_REG_INTERRUPT)
        irqa = await self.read(TCPC_REG_INTERRUPTA)
        irqb = await self.read(TCPC_REG_INTERRUPTB)
        if (irq & TCPC_REG_INTERRUPT_VBUSOK):
            if (await self.tcpm_get_vbus_level()):
                self._logger.info("IRQ: VBUSOK (VBUS=ON)")
                await self.evt_connect()
            else:
                self._logger.info("IRQ: VBUSOK (VBUS=OFF)")
                await self.evt_disconnect()
        if (irqa & TCPC_REG_INTERRUPTA_HARDRESET):
            self._logger.info("IRQ: HARDRESET")
            await self.evt_disconnect()
        if (irqb & TCPC_REG_INTERRUPTB_GCRCSENT):
            self._logger.info("IRQ: GCRCSENT")
            while (await self.fusb302_rx_fifo_is_empty() == 0):
                await self.evt_packet()

    async def status(self):
        status0 = await self.read(TCPC_REG_STATUS0)
        status1 = await self.read(TCPC_REG_STATUS1)
        status0a = await self.read(TCPC_REG_STATUS0A)
        status1a = await self.read(TCPC_REG_STATUS1A)


class ControlFUSB302Applet(I2CInitiatorApplet, name="control-fusb302"):
    logger = logging.getLogger(__name__)
    help = "configure FUSB302 USB-PD add-on"
    description = """
    Configure and control the FUSB302-based Glasgow USB-PD add-on
    """

    __pins = ("sda", "scl", "int", "ven", "fault")

    __registers = {
        TCPC_REG_DEVICE_ID:  "DeviceID",
        TCPC_REG_SWITCHES0:  "Switches0",
        TCPC_REG_SWITCHES1:  "Switches1",
        TCPC_REG_MEASURE:    "Measure",
        TCPC_REG_SLICE:      "Slice",
        TCPC_REG_CONTROL0:   "Control0",
        TCPC_REG_CONTROL1:   "Control1",
        TCPC_REG_CONTROL2:   "Control2",
        TCPC_REG_CONTROL3:   "Control3",
        TCPC_REG_MASK:       "Mask",
        TCPC_REG_POWER:      "Power",
        TCPC_REG_RESET:      "Reset",
        TCPC_REG_OCPREG:     "OCPreg",
        TCPC_REG_MASKA:      "MaskA",
        TCPC_REG_MASKB:      "MaskB",
        TCPC_REG_CONTROL4:   "Control4",
        TCPC_REG_STATUS0A:   "Status0A",
        TCPC_REG_STATUS1A:   "Status1A",
        TCPC_REG_INTERRUPTA: "InterruptA",
        TCPC_REG_INTERRUPTB: "InterruptB",
        TCPC_REG_STATUS0:    "Status0",
        TCPC_REG_STATUS1:    "Status1",
        TCPC_REG_INTERRUPT:  "Interrupt",
        TCPC_REG_FIFOS:      "FIFOs",
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
            await fusb302_iface.set_bits(TCPC_REG_RESET, 0x01)

        if (args.operation == "pd-reset"):
            await fusb302_iface.fusb302_pd_reset()

        if (args.operation == "hard-reset"):
            await fusb302_iface.fusb302_hard_reset()

        if (args.operation == "tcpm-init"):
            await fusb302_iface.tcpm_init()

        if (args.operation == "setup"):
            await fusb302_iface.setup()

        if (args.operation == "handle-irq"):
            await fusb302_iface.handle_irq()

        if (args.operation == "set-toggling"):
            await fusb302_iface.set_toggling(args.mode)
