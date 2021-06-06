import cocotb
from cocotb_helper import *
from test_rle_compressor_helper import *
from RL_helper import *
from multiprocessing import *
import numpy as np
import configparser
import ast
import logging
import math
import time

class CompressorCocotbEnv(CocotbEnv):
    def __init__(self, dut, observation_space):
        super().__init__()
        self.dut = dut
        self.tb = TestBench(dut)
        self.observation_space = observation_space
        self.history = ''

    @cocotb.coroutine
    def setup_rl_episode(self):
        self.cocotb_coverage.clear()
        self.clock_coroutine = cocotb.fork(self.clock_gen(self.dut.CLK,1))
        self.coverage_coroutine = cocotb.fork(monitor_signals(self.dut, self.cocotb_coverage, self.tb.count_width))   # tracks states covered
        self.history = ''    # to store the binary sequence for FSM based sequence generation
        yield Timer(1)
        yield self.assert_reset(self.dut.RST_N, 0, 1, 2)

    @cocotb.coroutine
    def rl_step(self):
        self.logger.info('cocotb | rl_step coroutine begin ')
        count_width = self.discrete_actions[0]
        print('count width', count_width)
        self.tb.count_width = count_width

        word_width = 4
        self.tb.word_width = word_width

        num_inputs = self.discrete_actions[1]
        print('N =', num_inputs)

        yield self.tb.input_drv.send(InputTransaction(self.tb, word_width, count_width,0,1,0,0,0))
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,0))
        yield RisingEdge(self.dut.CLK)

        self.drive_input_iter = 0
        while(self.drive_input_iter < num_inputs):
            verif_dut_drive_coroutine = cocotb.fork(self.verify_dut_input_drive())
            yield verif_dut_drive_coroutine.join()

        self.rl_done = True

        self.logger.info('cocotb | rl_step coroutine end ')


    @cocotb.coroutine
    def verify_dut_input_drive(self):
        curr_state = get_next_state_of_FSM(self.history, self.FSM_STATES)
        if(self.dut.RDY_ma_get_input == 1):
            sample = random.random()
            if(sample < self.continuous_actions[curr_state]):
                dut_input = 0
                self.history += '0'
            else:
                dut_input = random.randint(1,0xFFFF)
                self.history += '1'
            yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,dut_input,0,1,0,0))
            yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,0))
            yield RisingEdge(self.dut.CLK)
            self.drive_input_iter = self.drive_input_iter + 1
        elif(self.dut.RDY_mav_send_compressed_value == 1):
            yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,1))
            yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,0))

    @cocotb.coroutine
    def terminate_rl_episode(self):
        self.logger.info('cocotb | dut drive terminate begin ')
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,1,0))
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,0))

        yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,1))
        for t in range(2):
            yield RisingEdge(self.dut.CLK)
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,0))

        yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,1))
        for t in range(2):
            yield RisingEdge(self.dut.CLK)
        yield self.tb.input_drv.send(InputTransaction(self.tb, 0,0,0,0,0,0,0))

        self.logger.info('cocotb | dut drive terminate end ')

        for n in range(20):
            yield RisingEdge(self.dut.CLK)

        self.clock_coroutine.kill()
        self.coverage_coroutine.kill()

        self.logger.info('cocotb | history | ' + self.history)


    def finish_experiment(self):
        self.tb.stop()


@cocotb.coroutine
def monitor_signals(dut, cocotb_coverage, count_width):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_word_counter.value == 16),
             (int)(dut.rg_zero_counter.value == 64),
             (int)(dut.rg_counter.value == (2**count_width - 2)),
             (int)(dut.rg_next_count != 0),
             (int)((dut.rg_zero_counter.value == 64) and (dut.rg_next_count != 0))]
        s = ''.join(map(str, s))
        cocotb_coverage.append(s)

@cocotb.test()
def run_test(dut):
    cocotb_env = CompressorCocotbEnv(dut, gym.spaces.Discrete(1))
    yield cocotb_env.run()
