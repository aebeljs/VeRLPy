import cocotb
from cocotb_helper import *
from test_coo_decompressor_helper import *
from RL_helper import *
from multiprocessing import *
import numpy as np
import configparser
import ast
import logging
import math
import time

class COODecompressorCocotbEnv(CocotbEnv):
    def __init__(self, dut):
        super().__init__()
        self.dut = dut
        self.tb = Testbench(dut)
        cocotb.fork(self.clock_gen(self.dut.CLK, 1))

    @cocotb.coroutine
    def setup_rl_run(self):
        self.cocotb_coverage.clear()
        self.coverage_coroutine = cocotb.fork(monitor_signals(self.dut, self.cocotb_coverage))   # tracks states covered
        self.enable_coroutine = cocotb.fork(en_decompressed_output(self.dut, self.tb))
        yield Timer(1) # needed?

    @cocotb.coroutine
    def assert_dut_reset_from_rl(self):
        yield self.assert_reset(self.dut.RST_N, 0, 1, 2)

    @cocotb.coroutine
    def verify_configure(self):
        self.index_width = self.discrete_actions[0]
        print('index width', self.index_width)
        self.logger.info('cocotb | index_width | ' + str(self.index_width))

        self.word_width = self.discrete_actions[1]
        print('word width', self.word_width)
        self.logger.info('cocotb | word_width | ' + str(self.word_width))
        yield RisingEdge(self.dut.CLK)

    @cocotb.coroutine
    def rl_step_dut_input_drive(self):
        n2 = 0
        ##Initial compressed input alone will have details of word width and index width
        compressed_input = random.randint(0, 2**56 - 1) << 8 | self.index_width << 4 | self.word_width
        while(n2 < 20):
            if(self.dut.RDY_ma_get_inputs == 1):
                yield self.tb.input_drv.send(InputTransaction(self.tb, 1, compressed_input))
                yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0))
                ##Input Randomisation
                compressed_input = random.randint(0, 2**64-1)
                yield RisingEdge(self.dut.CLK)
                yield RisingEdge(self.dut.CLK)
                yield RisingEdge(self.dut.CLK)
                n2 = n2 + 1
            else:
                yield RisingEdge(self.dut.CLK)

        self.rl_done = True

    def compute_rl_feedback(self):
        observation = 0
        info = {}
        return observation, info

    @cocotb.coroutine
    def terminate_dut_drive(self):
        print("Driven all inputs for this episode ")
        for delay in range(5):
            yield RisingEdge(self.dut.CLK)
        if(self.dut.RDY_ma_send_decompressed_output == 1):
            yield FallingEdge(self.dut.RDY_ma_send_decompressed_output)
        
        self.coverage_coroutine.kill()
        self.enable_coroutine.kill()
        for delay in range(10):
            yield RisingEdge(self.dut.CLK)

    def finish_experiment(self):
        self.tb.stop()
        yield RisingEdge(self.dut.CLK)

@cocotb.coroutine
def monitor_signals(dut, cocotb_coverage):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_block_counter.value == 16),
             (int)((dut.rg_word_width.value + dut.rg_index_width.value)%4 != 0),
             (int)(dut.rg_next_count != 0)]
        s = ''.join(map(str, s))
        cocotb_coverage.append(s)

@cocotb.test()
def run_test(dut):
    cocotb_env = COODecompressorCocotbEnv(dut)
    yield cocotb_env.run()
