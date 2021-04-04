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

class Driver(BusDriver):
    _signals = [
            'EN_ma_get_inputs',
            'ma_get_inputs_val',
            ]

    def __init__(self, dut):
        BusDriver.__init__(self, dut, None, dut.CLK)

class InputTransaction(object):

    def __init__(self,tb,
            EN_ma_get_inputs=0,
            ma_get_inputs_val=0,
            ):

        self.EN_ma_get_inputs = BinaryValue(EN_ma_get_inputs, tb.EN_width, False)
        self.ma_get_inputs_val = BinaryValue(ma_get_inputs_val, tb.input_width, False)

class Output_en_Driver(BusDriver):
    _signals = [
            'EN_ma_send_decompressed_output',
            ]

    def __init__(self, dut):
        BusDriver.__init__(self, dut, None, dut.CLK)

class Output_en_Transaction(object):

    def __init__(self,tb,
            EN_ma_send_decompressed_output=0,
            ):

        self.EN_ma_send_decompressed_output = BinaryValue(EN_ma_send_decompressed_output,
                tb.EN_width, False)


class InputMonitor(BusMonitor):

    _signals = [
            'EN_ma_get_inputs',
            'ma_get_inputs_val',
            'EN_ma_send_decompressed_output',
            'RDY_ma_get_inputs',
            'RDY_ma_send_decompressed_output',
            'RDY_mv_get_decompressed_output',
            ]

    def __init__(self,dut,callback=None,event=None):
        BusMonitor.__init__(self,dut,None,dut.CLK,dut.RST_N,callback=callback,event=event)
        self.name = "in"

    @coroutine
    def _monitor_recv(self):
        EN_inp_edge = RisingEdge(self.bus.EN_ma_get_inputs)
        while True:
            if((self.bus.EN_ma_get_inputs == 1 and self.bus.RDY_ma_get_inputs == 1) or
               (self.bus.EN_ma_send_decompressed_output == 1 and self.bus.RDY_ma_send_decompressed_output == 1)):
                #print('[IN_MON] {0:25} : {1}'.format('EN_ma_get_inputs',self.bus.EN_ma_get_inputs.value.integer))
                #print('[IN_MON] {0:25} : {1}'.format('ma_get_inputs',hex(self.bus.ma_get_inputs_val.value.integer)))
                #print('[IN_MON] {0:25} : {1}'.format('EN_ma_send_decompressed_output',self.bus.EN_ma_send_decompressed_output.value.integer))
                vec = (
                        self.bus.EN_ma_get_inputs.value.integer,
                        self.bus.ma_get_inputs_val.value.integer,
                        self.bus.EN_ma_send_decompressed_output.value.integer,
                        self.bus.RDY_mv_get_decompressed_output.value.integer
                        )
                self._recv(vec)

            yield RisingEdge(self.clock)


class OutputTransaction(object):

    def __init__(self, tb=None,
            RDY_ma_get_inputs=0,
            mv_get_decompressed_output=0,
            RDY_mv_get_decompressed_output=0,
            RDY_ma_send_decompressed_output=0,
            ):
        if RDY_ma_get_inputs is not None and isinstance(RDY_ma_get_inputs, int):
            RDY_ma_get_inputs = BinaryValue(RDY_ma_get_inputs, tb.RDY_width, False)
        if mv_get_decompressed_output is not None and isinstance(mv_get_decompressed_output, int):
            mv_get_decompressed_output = BinaryValue(mv_get_decompressed_output, tb.output_width,False)
        if RDY_mv_get_decompressed_output is not None and isinstance(RDY_mv_get_decompressed_output, int):
            RDY_mv_get_decompressed_output = BinaryValue(RDY_mv_get_decompressed_output, tb.RDY_width, False)
        if RDY_ma_send_decompressed_output is not None and isinstance(RDY_ma_send_decompressed_output, int):
            RDY_ma_send_decompressed_output = BinaryValue(RDY_ma_send_decompressed_output, tb.RDY_width, False)

        self.value = (
                RDY_ma_get_inputs,
                mv_get_decompressed_output,
                RDY_mv_get_decompressed_output,
                RDY_ma_send_decompressed_output

        )

class Monitor(BusMonitor):
    _signals = [
            'RDY_ma_get_inputs',
            'mv_get_decompressed_output',
            'RDY_mv_get_decompressed_output',
            'RDY_ma_send_decompressed_output'
    ]


    def __init__(self,dut,tb,callback=None,event=None):
        BusMonitor.__init__(self,dut,None,dut.CLK,dut.RST_N,callback=callback, event=event)
        self.name = "out"
        self.tb = tb

    @coroutine
    def _monitor_recv(self):
        outp_edge = RisingEdge(self.bus.RDY_mv_get_decompressed_output)
        while True:
            #if self.bus.RDY_mv_get_decompressed_output.value != 1:
            #    yield outp_edge
            #print('[DUT_MON] {0:<25} : {1}'.format('RDY_ma_get_inputs',self.bus.RDY_ma_get_inputs.value))
            #print('[DUT_MON] {0:<25} : {1}'.format('mv_get_decompressed_output',self.bus.mv_get_decompressed_output.value))
            #print('[DUT_MON] {0:<25} : {1}'.format('RDY_mv_get_decompressed_output',self.bus.RDY_mv_get_decompressed_output.value))
            #print('[DUT_MON] {0:<25} : {1}'.format('RDY_ma_send_decompressed_output',self.bus.RDY_ma_send_decompressed_output.value))

            vec = (
                self.bus.RDY_ma_get_inputs.value,
                self.bus.mv_get_decompressed_output.value,
                self.bus.RDY_mv_get_decompressed_output.value,
                self.bus.RDY_ma_send_decompressed_output.value)

            self._recv(vec)

            yield RisingEdge(self.clock)


class DUTScoreboard(Scoreboard):
    def compare(self, count, exp, got, log, **_):
        for i in range(count):
            # print(" ",i,exp[i],got[i])
            if(got[i] != exp[i]):
                print("Values mismatched")
                #exit(1)
            # else:
                # print("Values matched")


class Testbench(object):

    def __init__(self, dut):
        self.dut = dut
        self.stopped = False

        self.EN_width = 1
        self.RDY_width = 1
        self.input_width = 64
        self.output_width = 16

        self.input_drv = Driver(dut)
        self.input_mon = InputMonitor(dut, callback=self.model)

        self.outen_drv = Output_en_Driver(dut)

        init_val = OutputTransaction(self)
        self.mon = Monitor(dut, self, callback=self.append_dut_output)

        self.expected_output = []
        self.got_output = []
        self.scoreboard = DUTScoreboard(dut)
        self.scoreboard.add_interface(self.mon, self.expected_output)

        self.start_decompression = 1
        self.word_width = 4
        self.count_width = 4

        self.next_count = 0
        self.next_word = 0
        self.cont_count = 0

        self.decompress_word = 0
        self.compressed_word = 0
        self.compressed_count = 0
        self.zero_counter = 64
        self.word_counter = 64
        self.counter = 0

        self.count_valid = 0

        self.decompressed_output_count = 0

    def model(self, transaction):
        (
                EN_ma_get_inputs,
                ma_get_inputs_val,
                EN_ma_send_decompressed_output,
                RDY_mv_send_decompressed_output
        ) = transaction
        #print('[MODEL] {0:<25} : {1}'.format('EN_ma_get_inputs',EN_ma_get_inputs))
        #print('[MODEL] {0:<25} : {1}'.format('ma_get_inputs_val',hex(ma_get_inputs_val)))
        #print('[MODEL] {0:<25} : {1}'.format('EN_ma_send_decompressed_output',EN_ma_send_decompressed_output))

        if(EN_ma_get_inputs == 1):
            if(self.zero_counter == 64 and self.counter == 0 and self.decompress_word == 0):
                self.compressed_count = ma_get_inputs_val
                self.zero_counter = 0
                if(self.start_decompression == 1):
                    self.start_decompression = 0
                    self.word_width = (self.compressed_count & 0xF) * 4
                    self.compressed_count = self.compressed_count >> 4
                    self.count_width = self.compressed_count & 0xF
                    self.compressed_count = self.compressed_count >> 4
                    self.zero_counter = 8
                if(self.next_count == 0):
                    self.counter = (self.compressed_count & (2**self.count_width - 1))
                    self.compressed_count = self.compressed_count >> self.count_width
                    self.zero_counter = self.zero_counter + self.count_width
                else:
                    temp_count = self.compressed_count & (2**(self.count_width-self.next_count) - 1)
                    self.counter = temp_count << self.next_count | self.next_word
                    self.compressed_count = self.compressed_count >> (self.count_width - self.next_count)
                    self.zero_counter = self.zero_counter + self.count_width - self.next_count
                    self.next_count = 0
                    self.next_word = 0
                if(self.counter == 0):
                    self.decompress_word = 1
                    self.cont_count = 0
                    self.count_valid = 0
                elif(self.counter == 2**self.count_width - 1):
                    self.counter = 2**self.count_width - 2
                    self.cont_count = 1
                    self.decompress_word = 0
                    self.count_valid = 1
                else:
                    self.decompress_word = 0
                    self.cont_count = 0
                    self.count_valid = 1
            elif(self.word_counter == 64):
                self.compressed_word = ma_get_inputs_val
                self.word_counter = 0
            else:
                print("ERROR New input is not expected ")

        decompressed_output = 0
        if(EN_ma_send_decompressed_output == 1 and RDY_mv_send_decompressed_output == 1):
            if(self.decompress_word == 1 and self.word_counter != 64):
                decompressed_output = self.compressed_word & (2**self.word_width - 1)
                self.compressed_word = self.compressed_word >> self.word_width
                self.word_counter = self.word_counter + self.word_width
                #print("FROM MODEL : Decompressed output word ",hex(decompressed_output))
                self.expected_output.append(hex(decompressed_output))
                self.decompressed_output_count = self.decompressed_output_count + 1
                if(self.counter == 0 and self.count_valid == 1):
                    self.decompress_word = 1
                else:
                    self.decompress_word = 0
            elif(self.decompress_word == 0 and self.counter != 0):
                decompressed_output = 0
                self.counter = self.counter - 1
                #print("FROM MODEL : Decompressed output zero ",hex(decompressed_output))
                self.expected_output.append(hex(decompressed_output))
                self.decompressed_output_count = self.decompressed_output_count + 1
                if(self.counter == 0 and self.cont_count == 0):
                    self.decompress_word = 1
                self.count_valid = 0
            else:
                print("ERROR unexpected state")

            if(self.counter == 0 and self.zero_counter != 64):
                temp_count = self.zero_counter + self.count_width
                if(temp_count <= 64):
                    self.counter = self.compressed_count & (2**self.count_width - 1)
                    self.compressed_count = self.compressed_count >> self.count_width
                    self.zero_counter = self.zero_counter + self.count_width
                    self.count_valid = 1
                else:
                    self.zero_counter = 64
                    self.count_valid = 0
                    self.next_count = self.count_width - (temp_count - 64)
                    self.next_word = self.compressed_count
                if(self.cont_count == 1 and self.counter == 0 and self.count_valid == 1):
                    #print("1")
                    self.decompress_word = 1
                    self.count_valid = 0
                    temp_count = self.zero_counter + self.count_width
                    if(temp_count <= 64):
                        #print("2")
                        self.counter = self.compressed_count & (2**self.count_width - 1)
                        self.compressed_count = self.compressed_count >> self.count_width
                        self.zero_counter = self.zero_counter + self.count_width
                        self.count_valid = 1
                    else:
                        #print("3")
                        self.zero_counter = 64
                        self.next_count = self.count_width - (temp_count - 64)
                        self.next_word = self.compressed_count
                    self.cont_count = 0
                if(self.counter == 2**self.count_width - 1 and self.count_valid == 1):
                    #print("4")
                    self.counter = self.counter - 1
                    self.cont_count = 1
                elif(self.count_valid == 1):
                    #print("5")
                    if(self.counter == 0 and self.decompress_word == 0):
                        #print("6")
                        self.decompress_word = 1
                        self.count_valid = 0
                    else:
                        #print("7")
                        self.count_valid = 1
                    self.cont_count = 0
            elif(self.counter == 0):
                #print("8")
                self.count_valid = 0


        #print('[MODEL] {0:<25} : {1}'.format('word_width',self.word_width))
        #print('[MODEL] {0:<25} : {1}'.format('count_width',self.count_width))
        #print('[MODEL] {0:<25} : {1}'.format('next_count',self.next_count))
        #print('[MODEL] {0:<25} : {1}'.format('next_word',hex(self.next_word)))
        #print('[MODEL] {0:<25} : {1}'.format('compressed_word',hex(self.compressed_word)))
        #print('[MODEL] {0:<25} : {1}'.format('compressed_count',hex(self.compressed_count)))
        #print('[MODEL] {0:<25} : {1}'.format('zero_counter',self.zero_counter))
        #print('[MODEL] {0:<25} : {1}'.format('word_counter',self.word_counter))
        #print('[MODEL] {0:<25} : {1}'.format('counter',self.counter))
        #print('[MODEL] {0:<25} : {1}'.format('count_valid',self.count_valid))
        #print('[MODEL] {0:<25} : {1}'.format('cont_count',self.cont_count))
        #print('[MODEL] {0:<25} : {1}'.format('decompress_word',self.decompress_word))
        #print('[MODEL] {0:<25} : {1}'.format('decompressed output count',self.decompressed_output_count))


    def append_dut_output(self, transaction):
        (
                RDY_1,
                decompressed_output,
                RDY_2,
                RDY_3,
        ) = transaction
        if(RDY_2 == 1):
            #print('Output from DUT : ',hex(decompressed_output))
            self.got_output.append(hex(decompressed_output))

    def compare_outputs(self):
        self.scoreboard.compare(self.decompressed_output_count,self.expected_output,self.got_output,self.scoreboard.log)
        self.expected_output = []
        self.got_output = []
        self.decompressed_output_count = 0

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
def get_decompressed_output(dut,tb):
    while True:
        #yield RisingEdge(dut.CLK)
        if(dut.RDY_ma_send_decompressed_output != 1):
            yield RisingEdge(dut.RDY_ma_send_decompressed_output)
        yield tb.outen_drv.send(Output_en_Transaction(tb,1))
        yield FallingEdge(dut.RDY_ma_send_decompressed_output)
        yield tb.outen_drv.send(Output_en_Transaction(tb,0))
        #yield FallingEdge(dut.CLK)
        #else:
        #   yield RisingEdge(dut.CLK)
