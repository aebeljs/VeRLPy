import cocotb
from cocotb_helper import CocotbEnv
from test_coo_compressor_helper import Testbench, InputTransaction
from cocotb.triggers import RisingEdge
import numpy as np
import configparser
import ast
import logging
import math
import time
import random
import gym

class COOCompressorCocotbEnv(CocotbEnv):
    def __init__(self, dut, observation_space):
        super().__init__()
        self.dut = dut
        self.tb = Testbench(dut)
        self.observation_space = observation_space

    @cocotb.coroutine
    def setup_rl_episode(self):
        self.cocotb_coverage.clear()
        self.clock_coroutine = cocotb.fork(self.clock_gen(self.dut.CLK, 1))
        self.coverage_coroutine = cocotb.fork(monitor_signals(self.dut, self.cocotb_coverage))   # tracks states covered
        yield self.assert_reset(self.dut.RST_N, 0, 1, 2)

    @cocotb.coroutine
    def rl_step(self):
        self.index_width = self.discrete_actions[0]
        self.tb.index_width = self.index_width
        print('index width', self.index_width)
        self.logger.info('cocotb | index_width | ' + str(self.index_width))

        self.word_width = self.discrete_actions[1]
        self.tb.word_width = self.word_width
        print('word width', self.word_width)
        self.logger.info('cocotb | word_width | ' + str(self.word_width))

        yield self.tb.input_drv.send(InputTransaction(self.tb, self.word_width, self.index_width, 0, 1, 0, 0, 0))
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 0, 0))
        yield RisingEdge(self.dut.CLK)
        n2 = 0
        N2 = 100
        while(n2 < N2):
            if(self.dut.RDY_ma_get_input == 1):
                dut_input = random.randint(1, 2**63 - 1)
                yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, dut_input, 0, 1, 0, 0))
                yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 0, 0))
                n2 += 1
                yield RisingEdge(self.dut.CLK)
                yield RisingEdge(self.dut.CLK)
            elif(self.dut.RDY_mav_send_compressed_value == 1):
                yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 0, 1))
                yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 0, 0))
                yield RisingEdge(self.dut.CLK)
                yield RisingEdge(self.dut.CLK)
            else:
                yield RisingEdge(self.dut.CLK)

        self.rl_done = True

    @cocotb.coroutine
    def terminate_rl_episode(self):
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 1, 0))
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 0, 0))

        yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 0, 1))
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0, 0, 0, 0, 0, 0))
        yield RisingEdge(self.dut.CLK)
        yield RisingEdge(self.dut.CLK)
        for n in range(20):
            yield RisingEdge(self.dut.CLK)
        yield RisingEdge(self.dut.CLK)

        self.coverage_coroutine.kill()
        self.clock_coroutine.kill()

    def finish_experiment(self):
        self.tb.stop()

@cocotb.coroutine
def monitor_signals(dut, cocotb_coverage):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_block_counter.value == 16),
             (int)((dut.rg_block_length.value) % 4 != 0),
             (int)(dut.rg_next_count != 0)]
        s = ''.join(map(str, s))
        cocotb_coverage.append(s)

@cocotb.test()
def run_test(dut):
    cocotb_env = COOCompressorCocotbEnv(dut, gym.spaces.Discrete(1))
    yield cocotb_env.run()
