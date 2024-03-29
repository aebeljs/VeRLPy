import random
import sys
import cocotb
import logging as log
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb_bus.monitors import BusMonitor
from cocotb_bus.drivers import BusDriver
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory
from cocotb_bus.scoreboard import Scoreboard
from cocotb.result import TestFailure
from cocotb.clock import Clock


class Driver(BusDriver):
    """Drives inputs to DUT"""
    _signals = [
        #
        'ma_start_compression_word_width',
        'ma_start_compression_index_width',
        'ma_get_input_val',
        'EN_ma_start_compression',
        'EN_ma_get_input',
        'EN_ma_end_compression',
        'EN_mav_send_compressed_value',
    ]

    def __init__(self, dut):
        BusDriver.__init__(self, dut, None, dut.CLK)


class InputTransaction(object):
    """Transactions sent to Driver"""

    def __init__(self, tb,
                 #
                 ma_start_compression_word_width=0,
                 ma_start_compression_index_width=0,
                 ma_get_input_val=0,
                 EN_ma_start_compression=0,
                 EN_ma_get_input=0,
                 EN_ma_end_compression=0,
                 EN_mav_send_compressed_value=0,
                 ):
        #
        self.ma_start_compression_word_width = BinaryValue(
            ma_start_compression_word_width, tb.max_word_width, False)
        self.ma_start_compression_index_width = BinaryValue(
            ma_start_compression_index_width, tb.max_count_width, False)
        self.ma_get_input_val = BinaryValue(
            ma_get_input_val, tb.input_length, False)
        self.EN_ma_start_compression = BinaryValue(
            EN_ma_start_compression, tb.EN_bits, False)
        self.EN_ma_get_input = BinaryValue(EN_ma_get_input, tb.EN_bits, False)
        self.EN_ma_end_compression = BinaryValue(
            EN_ma_end_compression, tb.EN_bits, False)
        self.EN_mav_send_compressed_value = BinaryValue(
            EN_mav_send_compressed_value, tb.EN_bits, False)


class InputMonitor(BusMonitor):
    """Passive input monitor of DUT"""
    _signals = [
        #
        'ma_start_compression_word_width',
        'ma_start_compression_index_width',
        'ma_get_input_val',
        'EN_ma_start_compression',
        'EN_ma_get_input',
        'EN_ma_end_compression',
        'EN_mav_send_compressed_value',
        'RDY_ma_start_compression',
        'RDY_ma_get_input',
        'RDY_ma_end_compression',
    ]

    def __init__(self, dut, callback=None, event=None):
        BusMonitor.__init__(self, dut, None,
                            dut.CLK, dut.RST_N,
                            callback=callback,
                            event=event)
        self.name = "in"

    @coroutine
    def _monitor_recv(self):
        EN_inp_edge = RisingEdge(self.bus.EN_ma_get_input)
        valid = False
        while True:
            # if self.bus.EN_ma_get_input.value.integer != 1 and self.bus.EN_ma_end_compression.value.integer != 1:
            #    yield EN_inp_edge
            if((self.bus.EN_ma_get_input.value.integer == 1 and self.bus.RDY_ma_get_input.value.integer == 1) or
              (self.bus.EN_ma_end_compression.value.integer == 1 and self.bus.RDY_ma_end_compression.value.integer == 1) or
              (self.bus.EN_ma_start_compression.value.integer == 1 and self.bus.RDY_ma_start_compression.value.integer == 1)):

                print('[IN_MON] {0:<25} : {1}'.format(
                    'ma_start_compression_word_width', self.bus.ma_start_compression_word_width.value.integer))
                print('[IN_MON] {0:<25} : {1}'.format(
                    'ma_start_compression_index_width', self.bus.ma_start_compression_index_width.value.integer))
                print('[IN_MON] {0:<25} : {1}'.format(
                    'ma_get_input_val', hex(self.bus.ma_get_input_val.value.integer)))
                print('[IN_MON] {0:<25} : {1}'.format(
                    'EN_ma_start_compression', self.bus.EN_ma_start_compression.value.integer))
                print('[IN_MON] {0:<25} : {1}'.format(
                    'EN_ma_get_input', self.bus.EN_ma_get_input.value.integer))
                print('[IN_MON] {0:<25} : {1}'.format(
                    'EN_ma_end_compression', self.bus.EN_ma_end_compression.value.integer))
                print('[IN_MON] {0:<25} : {1}'.format(
                    'EN_mav_send_compressed_value', self.bus.EN_mav_send_compressed_value.value.integer))
                
                vec = (
                    #
                    self.bus.ma_start_compression_word_width.value.integer,
                    self.bus.ma_start_compression_index_width.value.integer,
                    self.bus.ma_get_input_val.value.integer,
                    self.bus.EN_ma_start_compression.value.integer,
                    self.bus.EN_ma_get_input.value.integer,
                    self.bus.EN_ma_end_compression.value.integer,
                    self.bus.EN_mav_send_compressed_value.value.integer
                )
                self._recv(vec)

            yield RisingEdge(self.clock)
            # yield RisingEdge(self.clock)
            valid = False


class OutputTransaction(object):
    """ Transaction to be expected / received by OutputMonitor"""

    def __init__(self, tb=None,
                 #
                 RDY_ma_start_compression=0,
                 RDY_ma_get_input=0,
                 mav_send_compressed_value=0,
                 RDY_mav_send_compressed_value=0,
                 RDY_ma_end_compression=0,
                 mv_compression_done=0,
                 RDY_mv_compression_done=0,
                 ):
        """For expected transactions, value 'None' means don't care.
        tb must be an instance of the Testbench class."""
#
        if RDY_ma_start_compression is not None and isinstance(RDY_ma_start_compression, int):
            RDY_ma_start_compression = BinaryValue(
                RDY_ma_start_compression, tb.RDY_bits, False)
        if RDY_ma_get_input is not None and isinstance(RDY_ma_get_input, int):
            RDY_ma_get_input = BinaryValue(
                RDY_ma_get_input, tb.RDY_bits, False)
        if mav_send_compressed_value is not None and isinstance(mav_send_compressed_value, int):
            mav_send_compressed_value = BinaryValue(
                mav_send_compressed_value, tb.output_bits, False)
        if RDY_mav_send_compressed_value is not None and isinstance(RDY_mav_send_compressed_value, int):
            RDY_mav_send_compressed_value = BinaryValue(
                RDY_mav_send_compressed_value, tb.RDY_bits, False)
        if RDY_ma_end_compression is not None and isinstance(RDY_ma_end_compression, int):
            RDY_ma_end_compression = BinaryValue(
                RDY_ma_end_compression, tb.RDY_bits, False)
        if mv_compression_done is not None and isinstance(mv_compression_done, int):
            mv_compression_done = BinaryValue(
                mv_compression_done, tb.bool_bits, False)
        if RDY_mv_compression_done is not None and isinstance(RDY_mv_compression_done, int):
            RDY_mv_compression_done = BinaryValue(
                RDY_mv_compression_done, tb.RDY_bits, False)
#
        self.value = (
            RDY_ma_start_compression,
            RDY_ma_get_input,
            mav_send_compressed_value,
            RDY_mav_send_compressed_value,
            RDY_ma_end_compression,
            mv_compression_done,
            RDY_mv_compression_done
        )


class Monitor(BusMonitor):
    """Observes signals of DUT"""
    _signals = [
        #
        'RDY_ma_start_compression',
        'RDY_ma_get_input',
        'mav_send_compressed_value',
        'RDY_mav_send_compressed_value',
        'RDY_ma_end_compression',
        'mv_compression_done',
        'RDY_mv_compression_done',
        'EN_mav_send_compressed_value'
    ]

    def __init__(self, dut, tb, callback=None, event=None):
        BusMonitor.__init__(self, dut, None, dut.CLK, dut.RST_N,
                            callback=callback, event=event)
        self.name = "out"
        self.tb = tb

    @coroutine
    def _monitor_recv(self):
        outp_ready_edge = RisingEdge(self.bus.RDY_mav_send_compressed_value)
        while True:
            if self.bus.RDY_mav_send_compressed_value.value != 1:
                yield outp_ready_edge
            elif self.bus.EN_mav_send_compressed_value.value == 1:
                
                print('[DUT_MON] {0:<25} : {1}'.format(
                    'RDY_ma_start_compression ', self.bus.RDY_ma_start_compression.value))
                print('[DUT_MON] {0:<25} : {1}'.format(
                    'RDY_ma_get_input ', self.bus.RDY_ma_get_input.value))
                print('[DUT_MON] {0:<25} : {1}'.format(
                    'mav_send_compressed_value ', hex(self.bus.mav_send_compressed_value.value)))
                print('[DUT_MON] {0:<25} : {1}'.format(
                    'RDY_mav_send_compressed_value ', self.bus.RDY_mav_send_compressed_value.value))
                print('[DUT_MON] {0:<25} : {1}'.format(
                    'RDY_ma_end_compression ', self.bus.RDY_ma_end_compression.value))
                print('[DUT_MON] {0:<25} : {1}'.format(
                    'mv_compression_done ', self.bus.mv_compression_done.value))
                print('[DUT_MON] {0:<25} : {1}'.format(
                    'RDY_mv_compression_done ', self.bus.RDY_mv_compression_done.value))
                
                self._recv(OutputTransaction(self.tb,
                                             #
                                             self.bus.RDY_ma_start_compression.value,
                                             self.bus.RDY_ma_get_input.value,
                                             hex(self.bus.mav_send_compressed_value.value),
                                             self.bus.RDY_mav_send_compressed_value.value,
                                             self.bus.RDY_ma_end_compression.value,
                                             hex(self.bus.mv_compression_done.value),
                                             self.bus.RDY_mv_compression_done.value
                                             ))
            yield RisingEdge(self.clock)


class DUTScoreboard(Scoreboard):
    def compare(self, got, exp, log, **_):
        #print("Values reached Scoreboard \n")
        #print("exp")
        #print(exp.value[2])
        #print(exp.value[3])
        #print("got")
        #print(got.value[2])
        #print(got.value[3])
        if(got.value[2] != exp.value[2]):
            print("Values mismatched")
            print(exp.value[2])
            # print(exp.value[3])
            print("got")
            print(got.value[2])
            # print(got.value[3])
            #exit(1)
        #else:
        #   print("Values matched")


class TestBench(object):
    """Verification Test Bench"""

    def __init__(self, dut):
        self.dut = dut
        self.stopped = False

        """Signal length"""
#
        self.EN_bits = 1
        self.RDY_bits = 1
        self.output_bits = 64
        self.bool_bits = 1
        self.max_word_width = 4
        self.max_count_width = 4
        self.input_length = 64

        self.word_width = 4
        self.index_width = 4

        self.input_drv = Driver(dut)

        self.input_mon = InputMonitor(dut, callback=self.model)

        init_val = OutputTransaction(self)

        self.mon = Monitor(dut, self)

        self.expected_output = []
        self.scoreboard = DUTScoreboard(dut)
        #self.scoreboard.add_interface(self.mon, self.expected_output)

        self.word_counter = 0
        self.zero_counter = 0
        self.counter = 0
        self.compressed_word = 0
        self.compressed_zero_count = 0

    def model(self, transaction):
        """Model"""
#
        (
            ma_start_compression_word_width,
            ma_start_compression_index_width,
            ma_get_input_val,
            EN_ma_start_compression,
            EN_ma_get_input,
            EN_ma_end_compression,
            EN_mav_send_compressed_value
        ) = transaction

        RDY_ma_start_compression = 0
        RDY_ma_get_input = 0
        mav_send_compressed_value = 0
        RDY_mav_send_compressed_value = 0
        RDY_ma_end_compression = 0
        mv_compression_done = 0
        RDY_mv_compression_done = 0


        '''
        print('[MODEL] {0:<25} : {1}'.format('Input to model ', hex(ma_get_input_val)))
        print('[MODEL] {0:<25} : {1}'.format(
            'RDY_ma_start_compression ', RDY_ma_start_compression))
        print('[MODEL] {0:<25} : {1}'.format(
            'RDY_ma_get_input ', RDY_ma_get_input))
        print('[MODEL] {0:<25} : {1}'.format(
            'mav_send_compressed_value ', hex(mav_send_compressed_value)))
        print('[MODEL] {0:<25} : {1}'.format(
            'RDY_mav_send_compressed_value ', RDY_mav_send_compressed_value))
        print('[MODEL] {0:<25} : {1}'.format(
            'RDY_ma_end_compression ', RDY_ma_end_compression))
        print('[MODEL] {0:<25} : {1}'.format(
            'mv_compression_done ', mv_compression_done))
        print('[MODEL] {0:<25} : {1}'.format(
            'RDY_mv_compression_done ', RDY_mv_compression_done))
        print('[MODEL] {0:<25} : {1}'.format(
            'zero counter ', self.zero_counter))
        print('[MODEL] {0:<25} : {1}'.format('counter ', self.counter))
        print('[MODEL] {0:<25} : {1}'.format(
            'compressed_zero_count ', hex(self.compressed_zero_count)))
        print('[MODEL] {0:<25} : {1}'.format(
            'word counter ', self.word_counter))
        print('[MODEL] {0:<25} : {1}'.format(
            'compressed_word ', hex(self.compressed_word)))
        '''

    def stop(self):
        self.stopped = True


@cocotb.coroutine
def clock_gen(signal):
    while True:
        signal <= 0
        yield Timer(1)
        signal <= 1
        yield Timer(1)


@cocotb.coroutine
def monitor_signals(dut):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_block_counter.value == 16),
             (int)((dut.rg_block_length.value)%4 != 0),
             (int)(dut.rg_next_count != 0)]
        print(s)

@cocotb.test()
def run_test(dut):
    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut))

    tb = TestBench(dut)

    n1=0
    N1 = 5
    while(n1 < N1):
        n1=n1+1
        word_width = random.randint(1,8)
        index_width = random.randint(1,8)

        tb.word_width = word_width
        tb.index_width = index_width

        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        yield tb.input_drv.send(InputTransaction(tb,word_width,index_width,0,1,0,0,0))
        yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,0,0))
        yield RisingEdge(dut.CLK)
        n2 = 0
        N2 = 10
        while(n2 < N2):
            if(dut.RDY_ma_get_input == 1):
                dut_input = random.randint(1,2**63-1)
                yield tb.input_drv.send(InputTransaction(tb,0,0,dut_input,0,1,0,0))
                yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,0,0))
                n2=n2+1
                yield RisingEdge(dut.CLK)
                yield RisingEdge(dut.CLK)
            elif(dut.RDY_mav_send_compressed_value == 1):
                yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,0,1))
                yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,0,0))
                yield RisingEdge(dut.CLK)
                yield RisingEdge(dut.CLK)
            else:
                yield RisingEdge(dut.CLK)

        yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,1,0))
        yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,0,0))

        yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,0,1))
        yield tb.input_drv.send(InputTransaction(tb,0,0,0,0,0,0,0))
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)
        for n in range(20):
            yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

    tb.stop()
