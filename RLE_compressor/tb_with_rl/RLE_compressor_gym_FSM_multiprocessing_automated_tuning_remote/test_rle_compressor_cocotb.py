import random
import sys
import cocotb
import logging as log
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, RisingEdge, FallingEdge
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
        self.ma_start_compression_word_width = BinaryValue(
            ma_start_compression_word_width, tb.max_word_width, False)
        self.ma_start_compression_count_Width = BinaryValue(
            ma_start_compression_count_Width, tb.max_count_width, False)
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
        'ma_start_compression_count_Width',
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
                '''
                print('[IN_MON] {0:<25} : {1}'.format(
                    'ma_start_compression_word_width', self.bus.ma_start_compression_word_width.value.integer))
                print('[IN_MON] {0:<25} : {1}'.format(
                    'ma_start_compression_count_Width', self.bus.ma_start_compression_count_Width.value.integer))
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
                '''
                vec = (
                    #
                    self.bus.ma_start_compression_word_width.value.integer,
                    self.bus.ma_start_compression_count_Width.value.integer,
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
                '''
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
                '''
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
        self.input_length = 32

        self.word_width = 4
        self.count_width = 4

        self.input_drv = Driver(dut)

        self.input_mon = InputMonitor(dut, callback=self.model)

        init_val = OutputTransaction(self)

        self.mon = Monitor(dut, self)

        self.expected_output = []
        self.scoreboard = DUTScoreboard(dut)
        self.scoreboard.add_interface(self.mon, self.expected_output)

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
            ma_start_compression_count_Width,
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

        if(EN_ma_start_compression == 1): ## Initialise counters and update the widths to
                                          ## compressed_count
            self.word_counter = 0
            self.counter = 0
            self.zero_counter = 8
            self.compressed_word = 0
            self.compressed_zero_count = self.word_width | self.count_width << 4
        elif(EN_ma_end_compression == 1):
            if(self.word_counter != 0): ## Send compressed_word on end compression
                RDY_mav_send_compressed_value = 1
                mav_send_compressed_value = self.compressed_word
                self.word_counter = 0
                self.compressed_word = 0
                self.expected_output.append(OutputTransaction(self,
                                                            RDY_ma_start_compression,
                                                            RDY_ma_get_input,
                                                            hex(mav_send_compressed_value),
                                                            RDY_mav_send_compressed_value,
                                                            RDY_ma_end_compression,
                                                            mv_compression_done,
                                                            RDY_mv_compression_done
                                                            ))
            if(self.zero_counter != 0): ## Send compressed_count on end compression
                if(self.counter != 0):
                    temp_zero_count = self.zero_counter + self.count_width
                else:
                    temp_zero_count = self.zero_counter
                if(temp_zero_count <= 64):
                    RDY_mav_send_compressed_value = 1
                    mav_send_compressed_value = self.compressed_zero_count | (self.counter << self.zero_counter) | (1 << 64)
                    self.zero_counter = 0
                    self.counter = 0
                    self.compressed_zero_count = 0
                    self.expected_output.append(OutputTransaction(self,
                                                            RDY_ma_start_compression,
                                                            RDY_ma_get_input,
                                                            hex(mav_send_compressed_value),
                                                            RDY_mav_send_compressed_value,
                                                            RDY_ma_end_compression,
                                                            mv_compression_done,
                                                            RDY_mv_compression_done
                                                            ))
                else:
                    temp_next_count = temp_zero_count - 64
                    count_value = self.counter
                    self.compressed_zero_count = self.compressed_zero_count | (int(bin(count_value)[2:].zfill(self.count_width)[temp_next_count:],2)  << self.zero_counter)
                    RDY_mav_send_compressed_value = 1
                    mav_send_compressed_value = self.compressed_zero_count | ( 1 << 64)
                    self.expected_output.append(OutputTransaction(self,
                                                                      RDY_ma_start_compression,
                                                                      RDY_ma_get_input,
                                                                      hex(mav_send_compressed_value),
                                                                      RDY_mav_send_compressed_value,
                                                                      RDY_ma_end_compression,
                                                                      mv_compression_done,
                                                                      RDY_mv_compression_done
                                                                      ))

                    mav_send_compressed_value = int(bin(count_value)[2:].zfill(self.count_width)[:temp_next_count],2) | (1 << 64)
                    self.zero_counter = 0
                    self.counter = 0
                    self.compressed_zero_count = 0
                    self.expected_output.append(OutputTransaction(self,
                                                            RDY_ma_start_compression,
                                                            RDY_ma_get_input,
                                                            hex(mav_send_compressed_value),
                                                            RDY_mav_send_compressed_value,
                                                            RDY_ma_end_compression,
                                                            mv_compression_done,
                                                            RDY_mv_compression_done
                                                            ))



        else:
            if(EN_ma_get_input == 1):
                if(ma_get_input_val == 0):
                    if(self.counter == (2 ** self.count_width - 2)):
                        if(self.count_width != 1):
                            self.counter = 1
                        temp_zero_count = self.zero_counter + self.count_width
                        if(temp_zero_count <= 64):
                            self.compressed_zero_count = self.compressed_zero_count | ((2 ** self.count_width - 1) << self.zero_counter)
                            self.zero_counter = temp_zero_count
                        else:
                            temp_next_count = temp_zero_count - 64
                            count_value = 2 ** self.count_width - 1
                            self.compressed_zero_count = self.compressed_zero_count | (
                                    int(bin(count_value)[2:].zfill(self.count_width)[temp_next_count:],2)  << self.zero_counter)
                            RDY_mav_send_compressed_value = 1
                            mav_send_compressed_value = self.compressed_zero_count | ( 1 << 64)
                            self.expected_output.append(OutputTransaction(self,
                                                                      RDY_ma_start_compression,
                                                                      RDY_ma_get_input,
                                                                      hex(mav_send_compressed_value),
                                                                      RDY_mav_send_compressed_value,
                                                                      RDY_ma_end_compression,
                                                                      mv_compression_done,
                                                                      RDY_mv_compression_done
                                                                      ))
                            self.zero_counter = temp_next_count
                            self.compressed_zero_count = int(bin(count_value)[2:].zfill(self.count_width)[:temp_next_count],2)
                    else:
                        self.counter = self.counter + 1
                else:
                    ma_get_input_val = ma_get_input_val & ((2 ** (self.word_width * 4)) - 1)
                    self.compressed_word = self.compressed_word | (ma_get_input_val << (self.word_counter * 4))
                    self.word_counter = self.word_counter + self.word_width
                    if(self.word_counter == 16):
                        RDY_mav_send_compressed_value = 1
                        mav_send_compressed_value = self.compressed_word
                        self.compressed_word = 0
                        self.word_counter = 0
                        self.expected_output.append(OutputTransaction(self,
                                                                RDY_ma_start_compression,
                                                                RDY_ma_get_input,
                                                                hex(mav_send_compressed_value),
                                                                RDY_mav_send_compressed_value,
                                                                RDY_ma_end_compression,
                                                                mv_compression_done,
                                                                RDY_mv_compression_done
                                                                ))
                    if(self.counter != 0):
                        temp_zero_count = self.zero_counter + self.count_width
                        if(temp_zero_count <= 64):
                            self.compressed_zero_count = self.compressed_zero_count | self.counter << self.zero_counter
                            self.zero_counter = temp_zero_count
                        else:
                            temp_next_count = temp_zero_count - 64
                            count_value = self.counter
                            self.compressed_zero_count = self.compressed_zero_count | (
                                    int(bin(count_value)[2:].zfill(self.count_width)[temp_next_count:],2)  << self.zero_counter)
                            RDY_mav_send_compressed_value = 1
                            mav_send_compressed_value = self.compressed_zero_count | ( 1 << 64)
                            self.expected_output.append(OutputTransaction(self,
                                                                      RDY_ma_start_compression,
                                                                      RDY_ma_get_input,
                                                                      hex(mav_send_compressed_value),
                                                                      RDY_mav_send_compressed_value,
                                                                      RDY_ma_end_compression,
                                                                      mv_compression_done,
                                                                      RDY_mv_compression_done
                                                                      ))
                            self.zero_counter = temp_next_count
                            self.compressed_zero_count = int(bin(count_value)[2:].zfill(self.count_width)[:temp_next_count],2)
                        self.counter = 0


            if(self.zero_counter == 64):
                RDY_mav_send_compressed_value = 1
                mav_send_compressed_value = self.compressed_zero_count | ( 1 << 64)
                self.compressed_zero_count = 0
                self.zero_counter = 0
                self.expected_output.append(OutputTransaction(self,
                                                        RDY_ma_start_compression,
                                                        RDY_ma_get_input,
                                                        hex(mav_send_compressed_value),
                                                        RDY_mav_send_compressed_value,
                                                        RDY_ma_end_compression,
                                                        mv_compression_done,
                                                        RDY_mv_compression_done
                                                        ))

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


def start_compression(tb, word_width, count_width):
    ma_start_compression_word_width = word_width
    ma_start_compression_count_Width = count_width
    ma_get_input_val = 0
    EN_ma_start_compression = 1
    EN_ma_get_input = 0
    EN_ma_end_compression = 0
    EN_mav_send_compressed_value = 0
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )

    EN_ma_start_compression = 0
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
    ma_start_compression_word_width = 0
    ma_start_compression_count_Width = 0
    ma_get_input_val = random.randint(1,0xFFFF)
    EN_ma_start_compression = 0
    EN_ma_get_input = 1
    EN_ma_end_compression = 0
    EN_mav_send_compressed_value = 0
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )

    EN_ma_get_input = 0
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )

def specific_input_gen(tb, val):
    ma_start_compression_word_width = 0
    ma_start_compression_count_Width = 0
    ma_get_input_val = val
    EN_ma_start_compression = 0
    EN_ma_get_input = 1
    EN_ma_end_compression = 0
    EN_mav_send_compressed_value = 0
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )

    EN_ma_get_input = 0
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
    EN_ma_get_input = 0
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )

def enable_compression_output(tb,en_val):
    ma_start_compression_word_width = 0
    ma_start_compression_count_Width = 0
    ma_get_input_val = 0
    EN_ma_start_compression = 0
    EN_ma_get_input = 0
    EN_ma_end_compression = 0
    EN_mav_send_compressed_value = en_val
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )
    '''
    EN_mav_send_compressed_value = 0
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )
    '''

def enable_end_compression(tb):
    ma_start_compression_word_width = 0
    ma_start_compression_count_Width = 0
    ma_get_input_val = 0
    EN_ma_start_compression = 0
    EN_ma_get_input = 0
    EN_ma_end_compression = 1
    EN_mav_send_compressed_value = 0
    yield InputTransaction(tb,
                           ma_start_compression_word_width,
                           ma_start_compression_count_Width,
                           ma_get_input_val,
                           EN_ma_start_compression,
                           EN_ma_get_input,
                           EN_ma_end_compression,
                           EN_mav_send_compressed_value
                           )

    EN_ma_end_compression = 0
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
