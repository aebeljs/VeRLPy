from ctypes import resize
import cocotb
from cocotb_helper import *
from RL_helper import *
from multiprocessing import *
import numpy as np
import configparser
import ast
import logging
import math
import time
from test_axi_fabric_helper import *

class AXI4CrossbarCocotbEnv(CocotbEnv):
    def __init__(self, dut, observation_space):
        super().__init__()
        self.dut = dut
        self.tb = TestBench(dut)
        self.observation_space = observation_space
        self.history = ''
        self.num_inputs = 100
        self.drive_input_iter = 0

        self.master_wr_addr_0 = 0
        self.master_wr_addr_1 = 0
        self.m0_array = np.zeros(10)
        self.m1_array = np.zeros(10)


    @cocotb.coroutine
    def setup_rl_episode(self):
        self.cocotb_coverage.clear()
        self.clock_coroutine = cocotb.fork(self.clock_gen(self.dut.CLK, 1))
        self.coverage_coroutine = cocotb.fork(monitor_signals(self.dut, self.cocotb_coverage))   # tracks states covered
        self.history = ''    # to store the binary sequence for FSM based sequence generation
        self.m0_array = np.zeros(10)
        self.m1_array = np.zeros(10)

        self.m0_coroutine = cocotb.fork(read_master_0_response(self.dut))
        self.m1_coroutine = cocotb.fork(read_master_1_response(self.dut))

        #self.m_coroutine = cocotb.fork(read_master_response(self.tb))

        self.s0_coroutine = cocotb.fork(send_slave_0_response(self.dut))
        self.s1_coroutine = cocotb.fork(send_slave_1_response(self.dut))
        self.s2_coroutine = cocotb.fork(send_slave_2_response(self.dut))
        self.s3_coroutine = cocotb.fork(send_slave_3_response(self.dut))
        self.s4_coroutine = cocotb.fork(send_slave_4_response(self.dut))
        self.s5_coroutine = cocotb.fork(send_slave_5_response(self.dut))
        self.s6_coroutine = cocotb.fork(send_slave_6_response(self.dut))
        self.s7_coroutine = cocotb.fork(send_slave_7_response(self.dut))
        self.s8_coroutine = cocotb.fork(send_slave_8_response(self.dut))
        self.s9_coroutine = cocotb.fork(send_slave_9_response(self.dut))

        yield Timer(1)
        yield self.assert_reset(self.dut.RST_N, 0, 1, 2)


    @cocotb.coroutine
    def rl_step(self):
        self.logger.info('cocotb | dut verify configure begin ')
        self.master_wr_addr_0 = self.discrete_actions[0]
        print('master_addr_0 = ', self.master_wr_addr_0)
        self.master_wr_addr_1 = self.discrete_actions[1]
        print('master_addr_1 = ', self.master_wr_addr_1)
        yield RisingEdge(self.dut.CLK)
        self.logger.info('cocotb | dut verify configure end ')

        self.logger.info('cocotb | rl step dut drive begin ')
        self.drive_input_iter=0
        min_addr = min(self.master_wr_addr_0,self.master_wr_addr_1)
        max_addr = max(self.master_wr_addr_0,self.master_wr_addr_1)
        while(self.drive_input_iter < self.num_inputs):
            m0_addr = random.randint(min_addr,max_addr)
            m1_addr = random.randint(min_addr,max_addr)
            verif_dut_drive_coroutine = cocotb.fork(self.verify_dut_input_drive(m0_addr,m1_addr))
            yield verif_dut_drive_coroutine.join()
        self.rl_done = True
        self.logger.info('cocotb | rl step dut drive end ')


    @cocotb.coroutine
    def verify_dut_input_drive(self,m0_addr,m1_addr):
        while True:
            if(self.dut.RDY_m_i_wr_addr_0_enq != 1 or self.dut.RDY_m_i_wr_addr_1_enq != 1):
                if(self.dut.RDY_m_i_wr_addr_0_enq != 1):
                    yield RisingEdge(self.dut.CLK)
                if(self.dut.RDY_m_i_wr_addr_1_enq != 1):
                    yield RisingEdge(self.dut.CLK)
            else:      
                #print("Driving Input",self.drive_input_iter,int(m0_addr/4096)-1,int(m1_addr/4096)-1,self.m0_array,self.m1_array)
                self.m0_array[int(m0_addr/4096)-1] = self.m0_array[int(m0_addr/4096)-1] + 1
                self.m1_array[int(m1_addr/4096)-1] = self.m1_array[int(m1_addr/4096)-1] + 1
                m0_addr = m0_addr << 29
                m1_addr = m1_addr << 29
                yield self.tb.master_input_drv.send(Master_Input_Transaction(self.tb,m0_addr,m1_addr,0,0,1,1,1,1))
                yield self.tb.master_input_drv.send(Master_Input_Transaction(self.tb,0,0,0,0,0,0,0,0))
                for delay in range(1):
                    yield RisingEdge(self.dut.CLK)
                self.drive_input_iter = self.drive_input_iter + 1
                break


    @cocotb.coroutine
    def terminate_rl_episode(self):
        self.logger.info('cocotb | dut drive terminate begin ')
        for n in range(1000):
            yield RisingEdge(self.dut.CLK)

        print("Slave count : ",self.master_wr_addr_0,self.master_wr_addr_1,self.m0_array,self.m1_array)
    
        self.m0_coroutine.kill()
        self.m1_coroutine.kill()

        #self.m_coroutine.kill()

        self.s0_coroutine.kill()
        self.s1_coroutine.kill()
        self.s2_coroutine.kill()
        self.s3_coroutine.kill()
        self.s4_coroutine.kill()
        self.s5_coroutine.kill()
        self.s6_coroutine.kill()
        self.s7_coroutine.kill()
        self.s8_coroutine.kill()
        self.s9_coroutine.kill()

        self.logger.info('cocotb | dut drive terminate end ')


        self.clock_coroutine.kill()
        self.coverage_coroutine.kill()

        self.logger.info('cocotb | history | ' + self.history)


    def finish_experiment(self):
        self.tb.stop()


@cocotb.coroutine
def monitor_signals(dut, cocotb_coverage):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.fabric_v_f_wr_mis_0.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_1.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_2.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_3.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_4.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_5.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_6.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_7.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_8.not_ring_full.value == 0),
             (int)(dut.fabric_v_f_wr_mis_9.not_ring_full.value == 0)]
        s = ''.join(map(str, s))
        cocotb_coverage.append(s)

@cocotb.test()
def run_test(dut):
    cocotb_env = AXI4CrossbarCocotbEnv(dut,gym.spaces.Discrete(1))
    yield cocotb_env.run()
