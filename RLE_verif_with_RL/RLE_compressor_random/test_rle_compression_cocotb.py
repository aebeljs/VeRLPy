import random
import sys
import cocotb
import logging as log
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, RisingEdge
from cocotb.monitors import BusMonitor
from cocotb.drivers import BusDriver
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory
from cocotb.scoreboard import Scoreboard
from cocotb.result import TestFailure
from cocotb.clock import Clock

# Parameters : In width - 16, out width - 32, coordinate - 15

class Driver(BusDriver):
    """Drives inputs to DUT"""
    _signals = [
        #
        'ma_start_compression_word_width',
        'ma_start_compression_count_Width',
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
                ma_start_compression_count_Width=0,
                ma_get_input_val=0,
                EN_ma_start_compression=0,
                EN_ma_get_input=0,
                EN_ma_end_compression=0,
                EN_mav_send_compressed_value=0,
                ):
        #
        self.ma_start_compression_word_width = BinaryValue(ma_start_compression_word_width, tb.max_word_width, False)
        self.ma_start_compression_count_Width = BinaryValue(ma_start_compression_count_Width, tb.max_count_width, False)
        self.ma_get_input_val = BinaryValue(ma_get_input_val, tb.input_length, False)
        self.EN_ma_start_compression = BinaryValue(EN_ma_start_compression, tb.EN_bits, False)
        self.EN_ma_get_input = BinaryValue(EN_ma_get_input, tb.EN_bits, False)
        self.EN_ma_end_compression = BinaryValue(EN_ma_end_compression, tb.EN_bits, False)
        self.EN_mav_send_compressed_value = BinaryValue(EN_mav_send_compressed_value, tb.EN_bits, False)

class InputMonitor(BusMonitor):
    """Passive input monitor of DUT"""
    _signals = [
        #
        'ma_start_compression_word_width',
        'ma_start_compression_count_Width',
        'ma_get_input_val',
        'EN_ma_start_compression',
        'EN_ma_get_input',
        'EN_ma_end_compression',
        'EN_mav_send_compressed_value',
        #'RDY_ma_get_input',
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

        while True:
            #if self.bus.EN_ma_get_input.value.integer != 1 and self.bus.RDY_ma_get_input:
            #    yield EN_inp_edge
            if self.bus.EN_ma_get_input.value.integer == 1:
                # print('[IN_MON] {0:<25} : {1}'.format('EN_ma_get_input', self.bus.EN_ma_get_input.value.integer))
                # print('[IN_MON] {0:<25} : {1}'.format('ma_get_input_val', self.bus.ma_get_input_val.value.integer))
                # print('[IN_MON] {0:<25} : {1}'.format('EN_ma_start_compression', self.bus.EN_ma_start_compression.value.integer))
                # print('[IN_MON] {0:<25} : {1}'.format('ma_start_compression_word_width', self.bus.ma_start_compression_word_width.value.integer))
                # print('[IN_MON] {0:<25} : {1}'.format('ma_start_compression_count_Width', self.bus.ma_start_compression_count_Width.value.integer))
                # print('[IN_MON] {0:<25} : {1}'.format('EN_ma_end_compression', self.bus.EN_ma_end_compression.value.integer))
                # print('[IN_MON] {0:<25} : {1}'.format('EN_mav_send_compressed_value', self.bus.EN_mav_send_compressed_value.value.integer))
                vec = (
                    #
                    self.bus.EN_ma_get_input.value.integer,
                    self.bus.ma_get_input_val.value.integer,
                    self.bus.EN_ma_start_compression.value.integer,
                    self.bus.ma_start_compression_word_width.value.integer,
                    self.bus.ma_start_compression_count_Width.value.integer,
                    self.bus.EN_ma_end_compression.value.integer,
                    self.bus.EN_mav_send_compressed_value.value.integer
                )
                self._recv(vec)
            yield RisingEdge(self.clock)


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
            RDY_ma_start_compression = BinaryValue(RDY_ma_start_compression, tb.RDY_bits, False)
        if RDY_ma_get_input is not None and isinstance(RDY_ma_get_input, int):
            RDY_ma_get_input = BinaryValue(RDY_ma_get_input, tb.RDY_bits, False)
        if mav_send_compressed_value is not None and isinstance(mav_send_compressed_value, int):
            mav_send_compressed_value = BinaryValue(mav_send_compressed_value, tb.output_bits, False)
        if RDY_mav_send_compressed_value is not None and isinstance(RDY_mav_send_compressed_value, int):
            RDY_mav_send_compressed_value = BinaryValue(RDY_mav_send_compressed_value, tb.RDY_bits, False)
        if RDY_ma_end_compression is not None and isinstance(RDY_ma_end_compression, int):
            RDY_ma_end_compression = BinaryValue(RDY_ma_end_compression, tb.RDY_bits, False)
        if mv_compression_done is not None and isinstance(mv_compression_done, int):
            mv_compression_done = BinaryValue(mv_compression_done, tb.bool_bits, False)
        if RDY_mv_compression_done is not None and isinstance(RDY_mv_compression_done, int):
            RDY_mv_compression_done = BinaryValue(RDY_mv_compression_done, tb.RDY_bits, False)
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
            yield outp_ready_edge
            if self.bus.RDY_mav_send_compressed_value.value == 1:
                # print('[DUT_MON] {0:<25} : {1}'.format('RDY_ma_start_compression ', self.bus.RDY_ma_start_compression.value))
                # print('[DUT_MON] {0:<25} : {1}'.format('RDY_ma_get_input ', self.bus.RDY_ma_get_input.value))
                # print('[DUT_MON] {0:<25} : {1}'.format('mav_send_compressed_value ', self.bus.mav_send_compressed_value.value))
                # print('[DUT_MON] {0:<25} : {1}'.format('RDY_mav_send_compressed_value ', self.bus.RDY_mav_send_compressed_value.value))
                # print('[DUT_MON] {0:<25} : {1}'.format('RDY_ma_end_compression ', self.bus.RDY_ma_end_compression.value))
                # print('[DUT_MON] {0:<25} : {1}'.format('mv_compression_done ', self.bus.mv_compression_done.value))
                # print('[DUT_MON] {0:<25} : {1}'.format('RDY_mv_compression_done ', self.bus.RDY_mv_compression_done.value))

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
        print("Values reached Scoreboard \n")
        print(exp)
        print(got)


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
        self.input_length = 32

        self.word_width = 4
        self.count_width = 4

        self.input_drv = Driver(dut)

        self.input_mon = InputMonitor(dut, callback=self.model)

        init_val = OutputTransaction(self)

        self.mon = Monitor(dut, self)

        self.expected_output = []
        #self.scoreboard = DUTScoreboard(dut)
        #self.scoreboard.add_interface(self.mon, self.expected_output)

    def model(self, transaction):
        """Model"""
#
        (
            ma_start_compression_word_width,
            ma_start_compression_count_Width,
            ma_get_input_val,
            EN_ma_start_compression,
            EN_ma_get_input,
            EN_ma_end_compression,
            EN_mav_send_compressed_value
        ) = transaction

        RDY_ma_start_compression=0
        RDY_ma_get_input=0
        mav_send_compressed_value=0
        RDY_mav_send_compressed_value=0
        RDY_ma_end_compression=0
        mv_compression_done=0
        RDY_mv_compression_done=0

        self.expected_output.append(OutputTransaction(self,
                                                        RDY_ma_start_compression,
                                                        RDY_ma_get_input,
                                                        hex(mav_send_compressed_value),
                                                        RDY_mav_send_compressed_value,
                                                        RDY_ma_end_compression,
                                                        mv_compression_done,
                                                        RDY_mv_compression_done
                                                      ))

    def stop(self):
        self.stopped = True


def start_compression(tb,word_width,count_width):
    ma_start_compression_word_width=word_width
    ma_start_compression_count_Width=count_width
    ma_get_input_val=0
    EN_ma_start_compression=1
    EN_ma_get_input=0
    EN_ma_end_compression=0
    EN_mav_send_compressed_value=0
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )

    EN_ma_start_compression=0
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )

def random_input_gen(tb):
    ma_start_compression_word_width=0
    ma_start_compression_count_Width=0
    ma_get_input_val=random.randint(0,0xFFFFFFFF)
    EN_ma_start_compression=0
    EN_ma_get_input=1
    EN_ma_end_compression=0
    EN_mav_send_compressed_value=0
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )

def zero_input_gen(tb):
    ma_start_compression_word_width=0
    ma_start_compression_count_Width=0
    ma_get_input_val=0
    EN_ma_start_compression=0
    EN_ma_get_input=1
    EN_ma_end_compression=0
    EN_mav_send_compressed_value=0
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )

def enable_compression_output(tb):
    ma_start_compression_word_width=0
    ma_start_compression_count_Width=0
    ma_get_input_val=0
    EN_ma_start_compression=0
    EN_ma_get_input=0
    EN_ma_end_compression=0
    EN_mav_send_compressed_value=1
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )

    EN_mav_send_compressed_value=0
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )


def enable_end_compression(tb):
    ma_start_compression_word_width=0
    ma_start_compression_count_Width=0
    ma_get_input_val=0
    EN_ma_start_compression=0
    EN_ma_get_input=0
    EN_ma_end_compression=1
    EN_mav_send_compressed_value=0
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )

    EN_ma_end_compression=0
    yield InputTransaction(tb,
                            ma_start_compression_word_width,
                            ma_start_compression_count_Width,
                            ma_get_input_val,
                            EN_ma_start_compression,
                            EN_ma_get_input,
                            EN_ma_end_compression,
                            EN_mav_send_compressed_value
                            )

@cocotb.coroutine
def clock_gen(signal):
    while True:
        signal <= 0
        yield Timer(1)
        signal <= 1
        yield Timer(1)
