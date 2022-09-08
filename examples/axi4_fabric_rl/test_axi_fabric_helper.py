import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb_bus.drivers import BusDriver
from cocotb.binary import BinaryValue

s0_resp_delay = 10
s1_resp_delay = 10
s2_resp_delay = 10
s3_resp_delay = 10
s4_resp_delay = 10
s5_resp_delay = 10
s6_resp_delay = 10
s7_resp_delay = 10
s8_resp_delay = 10
s9_resp_delay = 10

class Master_Input_Driver(BusDriver):
    """Drives inputs to DUT"""
    _signals = [
        #
        'm_i_wr_addr_0_enq_x',
        'm_i_wr_addr_1_enq_x',
        'm_i_wr_data_0_enq_x',
        'm_i_wr_data_1_enq_x',
        'EN_m_i_wr_addr_0_enq',
        'EN_m_i_wr_addr_1_enq',
        'EN_m_i_wr_data_0_enq',
        'EN_m_i_wr_data_1_enq',
        #'EN_m_o_wr_resp_0_deq',
        #'EN_m_o_wr_resp_1_deq',
    ]

    def __init__(self, dut):
        BusDriver.__init__(self, dut, None, dut.CLK)


class Master_Input_Transaction(object):
    """Transactions sent to Driver"""

    def __init__(self, tb,
                    m_i_wr_addr_0_enq_x = 0,
                    m_i_wr_addr_1_enq_x = 0,
                    m_i_wr_data_0_enq_x = 0,
                    m_i_wr_data_1_enq_x = 0,
                    EN_m_i_wr_addr_0_enq = 0,
                    EN_m_i_wr_addr_1_enq = 0,
                    EN_m_i_wr_data_0_enq = 0,
                    EN_m_i_wr_data_1_enq = 0,
                    #EN_m_o_wr_resp_0_deq = 0,
                    #EN_m_o_wr_resp_1_deq = 0,
                 ):
        #
        self.m_i_wr_addr_0_enq_x = BinaryValue(m_i_wr_addr_0_enq_x, tb.wr_addr_width, False)
        self.m_i_wr_addr_1_enq_x = BinaryValue(m_i_wr_addr_1_enq_x, tb.wr_addr_width, False)

        self.m_i_wr_data_0_enq_x = BinaryValue(m_i_wr_data_0_enq_x, tb.wr_data_width, False)
        self.m_i_wr_data_1_enq_x = BinaryValue(m_i_wr_data_1_enq_x, tb.wr_data_width, False)

        self.EN_m_i_wr_addr_0_enq = BinaryValue(EN_m_i_wr_addr_0_enq, tb.EN_width, False)
        self.EN_m_i_wr_addr_1_enq = BinaryValue(EN_m_i_wr_addr_1_enq, tb.EN_width, False)

        self.EN_m_i_wr_data_0_enq = BinaryValue(EN_m_i_wr_data_0_enq, tb.EN_width, False)
        self.EN_m_i_wr_data_1_enq = BinaryValue(EN_m_i_wr_data_1_enq, tb.EN_width, False)

        #self.EN_m_o_wr_resp_0_deq = BinaryValue(EN_m_o_wr_resp_0_deq, tb.EN_width, False)
        #self.EN_m_o_wr_resp_1_deq = BinaryValue(EN_m_o_wr_resp_1_deq, tb.EN_width, False)


class Slave_Input_Driver(BusDriver):
    """Drives inputs to DUT"""
    _signals = [
        's_i_wr_resp_0_enq_x',
        's_i_wr_resp_1_enq_x',
        's_i_wr_resp_2_enq_x',
        's_i_wr_resp_3_enq_x',
        's_i_wr_resp_4_enq_x',
        's_i_wr_resp_5_enq_x',
        's_i_wr_resp_6_enq_x',
        's_i_wr_resp_7_enq_x',
        's_i_wr_resp_8_enq_x',
        's_i_wr_resp_9_enq_x',
        'EN_s_o_wr_addr_0_deq',
        'EN_s_o_wr_addr_1_deq',
        'EN_s_o_wr_addr_2_deq',
        'EN_s_o_wr_addr_3_deq',
        'EN_s_o_wr_addr_4_deq',
        'EN_s_o_wr_addr_5_deq',
        'EN_s_o_wr_addr_6_deq',
        'EN_s_o_wr_addr_7_deq',
        'EN_s_o_wr_addr_8_deq',
        'EN_s_o_wr_addr_9_deq',
        'EN_s_o_wr_data_0_deq',
        'EN_s_o_wr_data_1_deq',
        'EN_s_o_wr_data_2_deq',
        'EN_s_o_wr_data_3_deq',
        'EN_s_o_wr_data_4_deq',
        'EN_s_o_wr_data_5_deq',
        'EN_s_o_wr_data_6_deq',
        'EN_s_o_wr_data_7_deq',
        'EN_s_o_wr_data_8_deq',
        'EN_s_o_wr_data_9_deq',
        'EN_s_i_wr_resp_0_enq',
        'EN_s_i_wr_resp_1_enq',
        'EN_s_i_wr_resp_2_enq',
        'EN_s_i_wr_resp_3_enq',
        'EN_s_i_wr_resp_4_enq',
        'EN_s_i_wr_resp_5_enq',
        'EN_s_i_wr_resp_6_enq',
        'EN_s_i_wr_resp_7_enq',
        'EN_s_i_wr_resp_8_enq',
        'EN_s_i_wr_resp_9_enq',
    ]

    def __init__(self, dut):
        BusDriver.__init__(self, dut, None, dut.CLK)


class Slave_Input_Transaction(object):
    """Transactions sent to Driver"""

    def __init__(self, tb,
                 #
                s_i_wr_resp_0_enq_x=0,
                s_i_wr_resp_1_enq_x=0,
                s_i_wr_resp_2_enq_x=0,
                s_i_wr_resp_3_enq_x=0,
                s_i_wr_resp_4_enq_x=0,
                s_i_wr_resp_5_enq_x=0,
                s_i_wr_resp_6_enq_x=0,
                s_i_wr_resp_7_enq_x=0,
                s_i_wr_resp_8_enq_x=0,
                s_i_wr_resp_9_enq_x=0,
                EN_s_o_wr_addr_0_deq=0,
                EN_s_o_wr_addr_1_deq=0,
                EN_s_o_wr_addr_2_deq=0,
                EN_s_o_wr_addr_3_deq=0,
                EN_s_o_wr_addr_4_deq=0,
                EN_s_o_wr_addr_5_deq=0,
                EN_s_o_wr_addr_6_deq=0,
                EN_s_o_wr_addr_7_deq=0,
                EN_s_o_wr_addr_8_deq=0,
                EN_s_o_wr_addr_9_deq=0,
                EN_s_o_wr_data_0_deq=0,
                EN_s_o_wr_data_1_deq=0,
                EN_s_o_wr_data_2_deq=0,
                EN_s_o_wr_data_3_deq=0,
                EN_s_o_wr_data_4_deq=0,
                EN_s_o_wr_data_5_deq=0,
                EN_s_o_wr_data_6_deq=0,
                EN_s_o_wr_data_7_deq=0,
                EN_s_o_wr_data_8_deq=0,
                EN_s_o_wr_data_9_deq=0,
                EN_s_i_wr_resp_0_enq=0,
                EN_s_i_wr_resp_1_enq=0,
                EN_s_i_wr_resp_2_enq=0,
                EN_s_i_wr_resp_3_enq=0,
                EN_s_i_wr_resp_4_enq=0,
                EN_s_i_wr_resp_5_enq=0,
                EN_s_i_wr_resp_6_enq=0,
                EN_s_i_wr_resp_7_enq=0,
                EN_s_i_wr_resp_8_enq=0,
                EN_s_i_wr_resp_9_enq=0,
                 ):
        #
        self.s_i_wr_resp_0_enq_x = BinaryValue(s_i_wr_resp_0_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_1_enq_x = BinaryValue(s_i_wr_resp_1_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_2_enq_x = BinaryValue(s_i_wr_resp_2_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_3_enq_x = BinaryValue(s_i_wr_resp_3_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_4_enq_x = BinaryValue(s_i_wr_resp_4_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_5_enq_x = BinaryValue(s_i_wr_resp_5_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_6_enq_x = BinaryValue(s_i_wr_resp_6_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_7_enq_x = BinaryValue(s_i_wr_resp_7_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_8_enq_x = BinaryValue(s_i_wr_resp_8_enq_x, tb.wr_resp_width, False)
        self.s_i_wr_resp_9_enq_x = BinaryValue(s_i_wr_resp_9_enq_x, tb.wr_resp_width, False)

        self.EN_s_o_wr_addr_0_deq = BinaryValue(EN_s_o_wr_addr_0_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_1_deq = BinaryValue(EN_s_o_wr_addr_1_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_2_deq = BinaryValue(EN_s_o_wr_addr_2_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_3_deq = BinaryValue(EN_s_o_wr_addr_3_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_4_deq = BinaryValue(EN_s_o_wr_addr_4_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_5_deq = BinaryValue(EN_s_o_wr_addr_5_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_6_deq = BinaryValue(EN_s_o_wr_addr_6_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_7_deq = BinaryValue(EN_s_o_wr_addr_7_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_8_deq = BinaryValue(EN_s_o_wr_addr_8_deq, tb.EN_width, False)
        self.EN_s_o_wr_addr_9_deq = BinaryValue(EN_s_o_wr_addr_9_deq, tb.EN_width, False)

        self.EN_s_o_wr_data_0_deq = BinaryValue(EN_s_o_wr_data_0_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_1_deq = BinaryValue(EN_s_o_wr_data_1_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_2_deq = BinaryValue(EN_s_o_wr_data_2_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_3_deq = BinaryValue(EN_s_o_wr_data_3_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_4_deq = BinaryValue(EN_s_o_wr_data_4_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_5_deq = BinaryValue(EN_s_o_wr_data_5_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_6_deq = BinaryValue(EN_s_o_wr_data_6_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_7_deq = BinaryValue(EN_s_o_wr_data_7_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_8_deq = BinaryValue(EN_s_o_wr_data_8_deq, tb.EN_width, False)
        self.EN_s_o_wr_data_9_deq = BinaryValue(EN_s_o_wr_data_9_deq, tb.EN_width, False)

        self.EN_s_i_wr_resp_0_enq = BinaryValue(EN_s_i_wr_resp_0_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_1_enq = BinaryValue(EN_s_i_wr_resp_1_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_2_enq = BinaryValue(EN_s_i_wr_resp_2_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_3_enq = BinaryValue(EN_s_i_wr_resp_3_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_4_enq = BinaryValue(EN_s_i_wr_resp_4_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_5_enq = BinaryValue(EN_s_i_wr_resp_5_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_6_enq = BinaryValue(EN_s_i_wr_resp_6_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_7_enq = BinaryValue(EN_s_i_wr_resp_7_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_8_enq = BinaryValue(EN_s_i_wr_resp_8_enq, tb.EN_width, False)
        self.EN_s_i_wr_resp_9_enq = BinaryValue(EN_s_i_wr_resp_9_enq, tb.EN_width, False)


class TestBench(object):
    """Verification Test Bench"""

    def __init__(self, dut):
        self.dut = dut
        self.stopped = False

        """Signal length"""
#
        self.EN_width = 1
        self.wr_addr_width = 69
        self.wr_data_width = 37
        self.wr_resp_width = 10
        #self.rd_addr_width = 69
        #self.rd_resp_width = 43

        self.master_input_drv = Master_Input_Driver(dut)
        self.slave_input_drv  = Slave_Input_Driver(dut)

        self.master_input_transaction = Master_Input_Transaction(self)
        self.slave_input_transaction = Slave_Input_Transaction(self)


    def stop(self):
        self.stopped = True


@cocotb.coroutine
def read_master_0_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_m_o_wr_resp_0_deq != 1):
            #print("\t AXI read master 0 response waiting for DEQ RDY ")
            yield RisingEdge(dut.CLK)
        else:
            dut.EN_m_o_wr_resp_0_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_m_o_wr_resp_0_deq <= 0
            count_0 = count_0 + 1
            #print("\t AXI read master 0 response : ",count_0,dut.RDY_m_o_wr_resp_0_deq)
            for delay in range(3):
                yield RisingEdge(dut.CLK)

@cocotb.coroutine
def read_master_1_response(dut):
    count_1 = 0
    while True:
        if(dut.RDY_m_o_wr_resp_1_deq != 1):
            #print("\t AXI read master 1 response waiting for DEQ RDY ")
            yield RisingEdge(dut.CLK)
        else:
            dut.EN_m_o_wr_resp_1_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_m_o_wr_resp_1_deq <= 0
            count_1 = count_1 + 1
            #print("\t AXI read master 1 response : ",count_1,dut.RDY_m_o_wr_resp_1_deq)
            for delay in range(3):
                yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_0_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_0_deq == 1 and dut.RDY_s_o_wr_data_0_deq == 1):
            dut.EN_s_o_wr_addr_0_deq <= 1
            dut.EN_s_o_wr_data_0_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_0_deq <= 0
            dut.EN_s_o_wr_data_0_deq <= 0
            for delay in range(s0_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_0_enq == 1):
                    dut.EN_s_i_wr_resp_0_enq <= 1
                    dut.s_i_wr_resp_0_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_0_enq <= 0
                    yield RisingEdge(dut.CLK)
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 0 request and response : ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_1_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_1_deq == 1 and dut.RDY_s_o_wr_data_1_deq == 1):
            dut.EN_s_o_wr_addr_1_deq <= 1
            dut.EN_s_o_wr_data_1_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_1_deq <= 0
            dut.EN_s_o_wr_data_1_deq <= 0
            for delay in range(s1_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_1_enq == 1):
                    dut.EN_s_i_wr_resp_1_enq <= 1
                    dut.s_i_wr_resp_1_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_1_enq <= 0
                    yield RisingEdge(dut.CLK)
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave  1 request and response : ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_2_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_2_deq == 1 and dut.RDY_s_o_wr_data_2_deq == 1):
            dut.EN_s_o_wr_addr_2_deq <= 1
            dut.EN_s_o_wr_data_2_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_2_deq <= 0
            dut.EN_s_o_wr_data_2_deq <= 0
            for delay in range(s2_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_2_enq == 1):
                    dut.EN_s_i_wr_resp_2_enq <= 1
                    dut.s_i_wr_resp_2_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_2_enq <= 0
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 2 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_3_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_3_deq == 1 and dut.RDY_s_o_wr_data_3_deq == 1):
            dut.EN_s_o_wr_addr_3_deq <= 1
            dut.EN_s_o_wr_data_3_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_3_deq <= 0
            dut.EN_s_o_wr_data_3_deq <= 0
            for delay in range(s3_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_3_enq == 1):
                    dut.EN_s_i_wr_resp_3_enq <= 1
                    dut.s_i_wr_resp_3_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_3_enq <= 0
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 3 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_4_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_4_deq == 1 and dut.RDY_s_o_wr_data_4_deq == 1):
            dut.EN_s_o_wr_addr_4_deq <= 1
            dut.EN_s_o_wr_data_4_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_4_deq <= 0
            dut.EN_s_o_wr_data_4_deq <= 0
            for delay in range(s4_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_4_enq == 1):
                    dut.EN_s_i_wr_resp_4_enq <= 1
                    dut.s_i_wr_resp_4_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_4_enq <= 0
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 4 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_5_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_5_deq == 1 and dut.RDY_s_o_wr_data_5_deq == 1):
            dut.EN_s_o_wr_addr_5_deq <= 1
            dut.EN_s_o_wr_data_5_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_5_deq <= 0
            dut.EN_s_o_wr_data_5_deq <= 0
            for delay in range(s5_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_5_enq == 1):
                    dut.EN_s_i_wr_resp_5_enq <= 1
                    dut.s_i_wr_resp_5_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_5_enq <= 0
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 5 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_6_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_6_deq == 1 and dut.RDY_s_o_wr_data_6_deq == 1):
            dut.EN_s_o_wr_addr_6_deq <= 1
            dut.EN_s_o_wr_data_6_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_6_deq <= 0
            dut.EN_s_o_wr_data_6_deq <= 0
            for delay in range(s6_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_6_enq == 1):
                    dut.EN_s_i_wr_resp_6_enq <= 1
                    dut.s_i_wr_resp_6_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_6_enq <= 0
                    yield RisingEdge(dut.CLK)
                    yield RisingEdge(dut.CLK)
                    yield RisingEdge(dut.CLK)
                    yield RisingEdge(dut.CLK)
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 6 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_7_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_7_deq == 1 and dut.RDY_s_o_wr_data_7_deq == 1):
            dut.EN_s_o_wr_addr_7_deq <= 1
            dut.EN_s_o_wr_data_7_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_7_deq <= 0
            dut.EN_s_o_wr_data_7_deq <= 0
            for delay in range(s7_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_7_enq == 1):
                    dut.EN_s_i_wr_resp_7_enq <= 1
                    dut.s_i_wr_resp_7_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_7_enq <= 0
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 7 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_8_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_8_deq == 1 and dut.RDY_s_o_wr_data_8_deq == 1):
            dut.EN_s_o_wr_addr_8_deq <= 1
            dut.EN_s_o_wr_data_8_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_8_deq <= 0
            dut.EN_s_o_wr_data_8_deq <= 0
            for delay in range(s8_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_8_enq == 1):
                    dut.EN_s_i_wr_resp_8_enq <= 1
                    dut.s_i_wr_resp_8_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_8_enq <= 0
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 8 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)

@cocotb.coroutine
def send_slave_9_response(dut):
    count_0 = 0
    while True:
        if(dut.RDY_s_o_wr_addr_9_deq == 1 and dut.RDY_s_o_wr_data_9_deq == 1):
            dut.EN_s_o_wr_addr_9_deq <= 1
            dut.EN_s_o_wr_data_9_deq <= 1
            yield RisingEdge(dut.CLK)
            dut.EN_s_o_wr_addr_9_deq <= 0
            dut.EN_s_o_wr_data_9_deq <= 0
            for delay in range(s9_resp_delay):
                yield RisingEdge(dut.CLK)
            while True:
                if(dut.RDY_s_i_wr_resp_9_enq == 1):
                    dut.EN_s_i_wr_resp_9_enq <= 1
                    dut.s_i_wr_resp_9_enq_x <= 0
                    yield RisingEdge(dut.CLK)
                    dut.EN_s_i_wr_resp_9_enq <= 0
                    break
                else:
                    yield RisingEdge(dut.CLK)
            count_0 = count_0 + 1
            #print("\t AXI read slave 9 request and send request: ",count_0)
        else:
            yield RisingEdge(dut.CLK)


@cocotb.coroutine
def clock_gen(clk_signal):
    while True:
        clk_signal <= 0
        yield Timer(1)
        clk_signal <= 1
        yield Timer(1)
