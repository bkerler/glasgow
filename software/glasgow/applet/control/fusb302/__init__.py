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

TCPC_TX_SOP = 0
TCPC_TX_SOP_PRIME = 1
TCPC_TX_SOP_PRIME_PRIME = 2
TCPC_TX_SOP_DEBUG_PRIME = 3
TCPC_TX_SOP_DEBUG_PRIME_PRIME = 4
TCPC_TX_HARD_RESET = 5
TCPC_TX_CABLE_RESET = 6
TCPC_TX_BIST_MODE_2 = 7

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

FUSB302_TKN_SOP = 0xE0
FUSB302_TKN_SOP1 = 0xC0
FUSB302_TKN_SOP2 = 0xA0
FUSB302_TKN_SOP1DB = 0x80
FUSB302_TKN_SOP2DB = 0x60
FUSB302_TKN_SOP_MASK = 0xE0
        
PD_SRC_DEF_VNC = ((1600//42) & 0x3F)
PD_SRC_1_5_VNC = ((1600//42) & 0x3F)
PD_SRC_3_0_VNC = ((2600//42) & 0x3F)
PD_SRC_DEF_RD_THRESH = ((200//42) & 0x3F)
PD_SRC_1_5_RD_THRESH = ((400//42) & 0x3F)
PD_SRC_3_0_RD_THRESH = ((800//42) & 0x3F)

PD_CTRL_GOOD_CRC = 1
PD_CTRL_GOTO_MIN = 2
PD_CTRL_ACCEPT = 3
PD_CTRL_REJECT = 4
PD_CTRL_PING = 5
PD_CTRL_PS_RDY = 6
PD_CTRL_GET_SOURCE_CAP = 7
PD_CTRL_GET_SINK_CAP = 8
PD_CTRL_DR_SWAP = 9
PD_CTRL_PR_SWAP = 10
PD_CTRL_VCONN_SWAP = 11
PD_CTRL_WAIT = 12
PD_CTRL_SOFT_RESET = 13
# 14-15 Reserved
# Used for REV 3.0
PD_CTRL_NOT_SUPPORTED = 16
PD_CTRL_GET_SOURCE_CAP_EXT = 17
PD_CTRL_GET_STATUS = 18
PD_CTRL_FR_SWAP = 19
PD_CTRL_GET_PPS_STATUS = 20
PD_CTRL_GET_COUNTRY_CODES = 21

PD_DATA_SOURCE_CAP = 1
PD_DATA_REQUEST = 2
PD_DATA_BIST = 3
PD_DATA_SINK_CAP = 4
# 5-14 Reserved for REV 2.0
PD_DATA_BATTERY_STATUS = 5
PD_DATA_ALERT = 6
PD_DATA_GET_COUNTRY_INFO = 7
# 8-14 Reserved for REV 3.0
PD_DATA_VENDOR_DEF = 15

PD_REV10 = 0
PD_REV20 = 1
PD_REV30 = 2

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

    async def write_block(self, addr, data):
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
        return await self.write_block(addr, [data])


    async def read_block(self, addr, size):
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
            self._logger.log(self._level, "FUSB302: unacked slave and register address write")
            return None

        # Check the ACK of the slave address write and register data read
        unacked, = await self.lower._data_read(1)
        data = await self.lower._data_read(size)
        if unacked != 0:
            self._logger.log(self._level, "FUSB302: unacked data read")
            return None

        self._logger.log(self._level, "FUSB302: acked data=<%s>", data.hex())
        return data


    async def read(self, addr):
        data = await self._check(self.read_block(addr, 1))
        return None if data == None else data[0]


    async def read_msg(self):
        addr = TCPC_REG_FIFOS
        size = 3
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

        # Check the ACK of the slave address and register address write
        unacked, = await self.lower._data_read(1)
        if unacked != 0:
            await self.lower._cmd_stop()
            self._logger.log(self._level, "FUSB302: unacked slave and register address write")
            return (None,None,None)

        # Check the ACK of the slave address and register data read
        unacked, = await self.lower._data_read(1)
        if unacked != 0:
            await self.lower._cmd_stop()
            self._logger.log(self._level, "FUSB302: unacked data read")
            return (None,None,None)

        buf = await self.lower._data_read(size)

        # Grab the header
        sop = buf[0] & FUSB302_TKN_SOP_MASK
        head = (buf[1] & 0xFF)
        head |= ((buf[2] << 8) & 0xFF00)
        len = ((head >> 12) & 7) * 4
        self._logger.info("MSG: sop = %02X, head = %04X, len = %d", sop, head, len)

        await self.lower._cmd_start()
        await self.lower._cmd_count(1)
        await self.lower._cmd_write()
        await self.lower._data_write([(self._i2c_addr << 1) | 1])
        await self.lower._cmd_count(len)
        await self.lower._cmd_read()
        await self.lower._cmd_stop()

        # Check the ACK of the slave address and register data read
        unacked, = await self.lower._data_read(1)
        if unacked != 0:
            await self.lower._cmd_stop()
            self._logger.log(self._level, "FUSB302: unacked data read")
            return (None,None,None)

        buf = await self.lower._data_read(len)
        return (sop,head,buf)

    
    async def mask_write(self, addr, mask, value):
        data = await self._check(self.read(addr))
        if (data == None): return None
        data &= ~mask
        data |= value
        return await self._check(self.write(addr, data))


    async def set_bits(self, addr, bits):
        return await self._check(self.mask_write(addr, 0, bits))


    async def clear_bits(self, addr, bits):
        return await self._check(self.mask_write(addr, bits, 0))


    async def write_msg(self, header, data, sop):
        self._logger.info("WRITE_MSG: start")
        addr = TCPC_REG_FIFOS

        reg = FUSB302_TKN_PACKSYM
        reg |= (self._get_num_bytes(header) & 0x1F)

        payload = []
        payload.extend(sop)
        payload.extend([reg, header & 0xFF, header >> 8])
        self._logger.info("WRITE_MSG: data = %s", data)
        for word in data:
            self._logger.info("WRITE_MSG: word = %04X", word)
            payload.append(word & 0xFF)
            payload.append((word >> 8) & 0xFF)
            payload.append((word >> 16) & 0xFF)
            payload.append((word >> 24) & 0xFF)
        payload.append(FUSB302_TKN_JAMCRC)
        payload.append(FUSB302_TKN_EOP)
        payload.append(FUSB302_TKN_TXOFF)
        payload.append(FUSB302_TKN_TXON)
        self._logger.info("WRITE_MSG: payload = %s", payload)

        # Perform the whole write/read transaction in one chunk, assuming success
        await self.lower._cmd_start()
        await self.lower._cmd_count(2 + len(payload))
        await self.lower._cmd_write()
        await self.lower._data_write([(self._i2c_addr << 1) | 0])
        await self.lower._data_write([addr])
        await self.lower._data_write(payload)
        await self.lower._cmd_stop()

        unacked, = await self.lower._data_read(1)
        acked = len(data) - unacked
        if unacked == 0:
            self._logger.log(self._level, "FUSB302: acked=%d", acked)
        else:
            self._logger.log(self._level, "FUSB302: unacked=%d", unacked)

        return unacked == 0

    
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
        return ((((header) >> 12) & 7) * 4) + 2


    async def fusb302_send_message(self, header, data, sop):
        await self.write_msg(header, data, sop)
        

    async def fusb302_tcpm_select_rp_value(self, rp):
        # TBD
        fail


    async def fusb302_tcpm_init(self):

        self._state = STATE_INVALID

        # set default
        self._msgid = 0
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


    async def fusb302_tcpm_get_message(self):
        # If our FIFO is empty then we have no packet
        if (await self.fusb302_rx_fifo_is_empty()):
            return None
        while (True):
            sop, head, buf = await self.read_msg()
            # Break if no message found
            if (sop == None): break
            # Break if not GoodCRC
            if (((head & 0x1F) != PD_CTRL_GOOD_CRC) or (((head >> 12) & 7) != 0)): break
            # Break if FIFO is empty
            if (await self.fusb302_rx_fifo_is_empty()): break
        return (sop, head, buf)

        
    async def fusb302_tcpm_transmit(self, type, header, data):
        await self.fusb302_flush_tx_fifo()
        header |= (self._msgid << 9)
        self._msgid += 1
        self._msgid &= 0x7;

        if (type == TCPC_TX_SOP):
            sop = [FUSB302_TKN_SYNC1, FUSB302_TKN_SYNC1, FUSB302_TKN_SYNC1, FUSB302_TKN_SYNC2]
            await self.fusb302_send_message(header, data, sop)
            return 0
        else:
            return 1

        
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


    async def vbus_off(self):
        # TBD
        pass
    

    async def evt_disconnect(self):
        self._logger.info("DEF: evt_disconnect")
        await self.vbus_off()
        await self.fusb302_pd_reset()
        await self.fusb302_tcpm_set_rx_enable(0)
        await self.fusb302_tcpm_set_cc(TYPEC_CC_RD);
        self._state = STATE_DISCONNECTED
        self._logger.info("S: DISCONNECTED")

        
    async def evt_connect(self):
        self._logger.info("DEF: evt_connect")
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

        
    def PD_HEADER(self, type, prole, drole, id, cnt, rev, ext):
        return ((type) | ((rev) << 6) |
                ((drole) << 5) | ((prole) << 8) |
                ((id) << 9) | ((cnt) << 12) | ((ext) << 15))

        
    async def send_power_request(self, cap):
        hdr = self.PD_HEADER(PD_DATA_REQUEST, 0, 0, 0, 1, PD_REV20, 0)
        req = ((1<<28) | # Object position (fixed 5V)
               (1<<25) | # USB communications capable
               (0<<10) | # 0mA operating
               (0<<0))   # 0mA max
        self._logger.info("POWER_REQ: req = %s", req)
        await self.fusb302_tcpm_transmit(TCPC_TX_SOP, hdr, [req]);
        self._logger.info(">REQUEST")


    async def handle_msg(self, sop, hdr, msg):
        len = (((hdr) >> 12) & 7)
        type = ((hdr) & 0x1F)
        if (len != 0):
            if (type == PD_DATA_SOURCE_CAP):
                self._logger.info("<SOURCE_CAP: %08X", msg[0])
                await self.send_power_request(msg[0]);
            else:
                self._logger.info("<UNK DATA: %02X", type)
        else:
            self._logger.info("<UNK CTRL: %02X", type)


    async def evt_packet(self):
        self._logger.info("DEF: evt_packet")
        sop,hdr,msg = await self.fusb302_tcpm_get_message()
        if (sop == None): return
        await self.handle_msg(sop, hdr, msg)

        
    async def handle_irq(self):
        # self._logger.info("DEF: handle_irq")
        irq = await self.read(TCPC_REG_INTERRUPT)
        irqa = await self.read(TCPC_REG_INTERRUPTA)
        irqb = await self.read(TCPC_REG_INTERRUPTB)
        if ((irq == 0) and (irqa == 0) and (irqb == 0)): return False
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
        return True

    async def status(self):
        status0 = await self.read(TCPC_REG_STATUS0)
        status1 = await self.read(TCPC_REG_STATUS1)
        status0a = await self.read(TCPC_REG_STATUS0A)
        status1a = await self.read(TCPC_REG_STATUS1A)


    async def connect_snk(self):
        self._logger.info("DEF: connect_snk")
        await self.fusb302_tcpm_init()
        await self.fusb302_pd_reset()
        await self.fusb302_tcpm_set_rx_enable(0)
        await self.fusb302_tcpm_set_cc(TYPEC_CC_OPEN)
        # Wait for events to flush
        while (await self.handle_irq()): pass
        # Setup for sink connection
        await self.evt_disconnect()
        # Wait for source to connect
        while (self._state == STATE_DISCONNECTED): await self.handle_irq()
        # Wait for source to send Source Caps
        while (True): await self.handle_irq()

class ControlFUSB302Applet(I2CInitiatorApplet, name="control-fusb302"):
    logger = logging.getLogger(__name__)
    help = "configure FUSB302 USB-PD add-on"
    description = """
    Configure and control the FUSB302-based Glasgow USB-PD add-on
    """

    _polling_period = 0.1

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

        alert, self.__addr_alert = target.registers.add_ro(1)

        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(I2CInitiatorSubtarget(
            pads=iface.get_pads(args, pins=("sda", "scl")),
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

        p_read_block = p_operation.add_parser(
            "read-block", help="read register block")
        p_read_block.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_read_block.add_argument(
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

        p_write_block = p_operation.add_parser(
            "write-block", help="write register block")
        p_write_block.add_argument(
            "address", metavar="ADDRESS", type=register,
            help="register address")
        p_write_block.add_argument(
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

        p_connect_snk = p_operation.add_parser(
            "connect-snk", help="connect as sink")

        p_handle_irq = p_operation.add_parser(
            "handle-irq", help="handle interrupts")

        p_set_toggling = p_operation.add_parser(
            "set-toggling", help="set toggling mode")
        p_set_toggling.add_argument("mode", choices=('none', 'src', 'snk', 'drp'),
                                    help="toggle mode")


    async def _monitor_alert(self, device, iface):
        while True:
            #alert = await device.read_register(self.__addr_alert, width=1)
            alert = 0
            if (alert):
                await iface.handle_irq()
            await asyncio.sleep(self._polling_period)

        
    async def repl(self, device, args, iface):

        await iface.connect_snk()
        self._polling_period = 1
        asyncio.create_task(self._monitor_alert(device, iface))

        await super().repl(device, args, iface)


    async def interact(self, device, args, iface):

        # await iface.connect_snk()
        # self._polling_period = 1
        # asyncio.create_task(self._monitor_alert(device, iface))

        if (args.operation == "read"):
            data = await iface.read(args.address)
            print(data.hex())

        if (args.operation == "read-block"):
            data = await iface.read_block(args.address, args.size)
            print(data.hex())

        if (args.operation == "write"):
            await iface.write(args.address, args.data)

        if (args.operation == "write-block"):
            await iface.write_block(args.address, args.data)

        if (args.operation == "mask-write"):
            await iface.mask_write(args.address, args.mask, args.data)

        if (args.operation == "set-bits"):
            await iface.set_bits(args.address, args.bits)

        if (args.operation == "clear-bits"):
            await iface.clear_bits(args.address, args.bits)

        if (args.operation == "read-all"):
            for address in self.__registers.keys():
                print("{:11s}[{:02X}]: {:02X}"
                      .format(self.__registers[address], address, (await iface.read(address))))

        if (args.operation == "sw-reset"):
            await iface.set_bits(TCPC_REG_RESET, 0x01)

        if (args.operation == "pd-reset"):
            await iface.fusb302_pd_reset()

        if (args.operation == "hard-reset"):
            await iface.fusb302_hard_reset()

        if (args.operation == "tcpm-init"):
            await iface.tcpm_init()

        if (args.operation == "connect-snk"):
            await iface.connect_snk()

        if (args.operation == "handle-irq"):
            await iface.handle_irq()

        if (args.operation == "set-toggling"):
            await iface.set_toggling(args.mode)
