import cocotb
from cocotb_env import *
from RL_helper import *
from multiprocessing import *
import numpy as np
import configparser
import ast
import logging
import math
import time

class CompressorCocotbEnv(CocotbEnv):
    import cocotb
    def __init__(self, dut):
        super().__init__()
        self.dut = dut
        self.tb = TestBench(dut)

    def setup_experiment(self):
        cocotb.fork(clock_gen(self.dut.CLK))

    @cocotb.coroutine
    def take_step(self):
        count_width = self.discrete_actions[0]
        print('count width', count_width)
        self.tb.count_width = count_width

        word_width = 4
        self.tb.word_width = word_width

        N = self.discrete_actions[1]
        print('N =', N)

        self.cocotb_coverage.clear()
        m_sig = cocotb.fork(monitor_signals(self.dut, self.cocotb_coverage, count_width))   # tracks states covered
        history = ''    # to store the binary sequence for FSM based sequence generation

        # reset the DUT
        self.dut.RST_N <= 0
        yield Timer(2)
        self.dut.RST_N <= 1

        start_comp = start_compression(self.tb, word_width, count_width)
        for t in start_comp:
            yield self.tb.input_drv.send(t)
        yield RisingEdge(self.dut.CLK)
        yield RisingEdge(self.dut.CLK)

        # take action
        n = 0
        while(n < N):
            curr_state = get_next_state_of_FSM(history, self.FSM_states)
            if(self.dut.RDY_ma_get_input == 1):
                sample = random.random()
                if(sample < self.continuous_actions[curr_state]):
                    input_gen = zero_input_gen(self.tb)
                    history += '0'
                else:
                    input_gen = random_input_gen(self.tb)
                    history += '1'
                for t in input_gen:
                    yield self.tb.input_drv.send(t)
                n = n + 1
                yield RisingEdge(self.dut.CLK)

            elif(self.dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(self.tb, 1)
                for t in output_enable:
                    yield self.tb.input_drv.send(t)

                output_enable = enable_compression_output(self.tb, 0)
                for t in output_enable:
                    yield self.tb.input_drv.send(t)

        end_comp = enable_end_compression(self.tb)
        for t in end_comp:
            yield self.tb.input_drv.send(t)

        output_enable = enable_compression_output(self.tb, 1)
        for t in output_enable:
            yield self.tb.input_drv.send(t)

        for t in range(2):
            yield RisingEdge(self.dut.CLK)

        output_enable = enable_compression_output(self.tb, 0)
        for t in output_enable:
            yield self.tb.input_drv.send(t)

        output_enable = enable_compression_output(self.tb, 1)
        for t in output_enable:
            yield self.tb.input_drv.send(t)

        for t in range(2):
            yield RisingEdge(self.dut.CLK)

        output_enable = enable_compression_output(self.tb, 0)
        for t in output_enable:
            yield self.tb.input_drv.send(t)

        for n in range(20):
            yield RisingEdge(self.dut.CLK)

        yield RisingEdge(self.dut.CLK)

        m_sig.kill()
        # write to a file the coverage, reward, etc.
        self.logger.info('cocotb | history | ' + history)


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
    cocotb_env = CompressorCocotbEnv(dut)
    yield cocotb_env.run()
