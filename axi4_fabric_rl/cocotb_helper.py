from abc import ABC, abstractmethod
import cocotb
from cocotb.triggers import Timer
from RL_helper import *
from multiprocessing import *
import numpy as np
import configparser
import ast
import logging
import math
import time

class CocotbEnv(ABC):
    def __init__(self):
        '''
        Initialization for the cocotb environment. For using any objects in
        addition to the ones initialized here, override __init__(self), with
        additional arguments if necessary, in the subclass and use
        super().__init__() to initialize the below objects followed by any other
        objects that are needed for the experiment (see example subclass).
        '''
        self.timestamp = str(int(time.time()))   # timestamp to tag the log file and model

        # set up the config file reader
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        # set up the logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self.timestamp + '.log')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        # set up the Pipe and start the RL process
        self.parent_conn, child_conn = Pipe()
        self.rl_process = Process(target=RL_run, args=(child_conn, self.logger, self.timestamp,))
        self.rl_process.start()

        # read parameters from config file
        self.NUM_STEPS = self.config['main'].getint('num_steps')
        self.FSM_STATES = ast.literal_eval(self.config['cocotb']['fsm_states'])

        # get the valid value set for each discrete parameter
        discrete_params = ast.literal_eval(self.config['cocotb']['discrete_params'])
        self.DISCRETE_PARAM_VALUES = []
        for param in discrete_params:
            self.DISCRETE_PARAM_VALUES.append(ast.literal_eval(self.config['discrete'][param]))

        self.rl_observation = 0
        self.rl_done = False
        self.rl_info = {}

        self.cocotb_coverage = []   # list to be populated with each episode's coverage
        self.discrete_actions = []  # list which will have the discrete actions in each episode
        self.continuous_actions = []    # list which will have the continuous actions in each episode

    @cocotb.coroutine
    def clock_gen(self, clk_signal, clk_delay):
        '''
        This coroutine can be used to initialize a clock signal in the DUT.

        Inputs
        clk_signal: The signal corresponding to the clock of the DUT should be
                    passed here
        clk_delay : The delay required for the clock signal - (Time period / 2)
        '''
        while True:
            clk_signal <= 0
            yield Timer(clk_delay)
            clk_signal <= 1
            yield Timer(clk_delay)

    @cocotb.coroutine
    def assert_reset(self, rst_signal, rst_val, rstn_val, rst_delay):
        '''
        This coroutine can be used to reset DUT.

        Inputs
        rst_signal: The signal corresponding to the reset of the DUT should be
                    passed here
        rst_val   : The value which needs to be assigned to the signal to assert
                    reset
        rstn_val  : The value which needs to be assigned to the signal after the
                    reset is done
        rst_delay : The delay required before the rstn_val is assigned to the
                    signal
        '''
        rst_signal <= rst_val
        yield Timer(rst_delay)
        rst_signal <= rstn_val

    @cocotb.coroutine
    @abstractmethod
    def setup_rl_episode(self):
        '''
        This coroutine will be called at the start of each RL episode when the
        reset() function of the gym environment is called. It can be used to
        start the coroutines such as DUT clock coroutines, coroutines which track 
        the register elements of interest in the DUT. See the loop in run(self) 
        below for the exact call location. This method must be overridden in the subclass.
        The list self.cocotb_coverage must be populated with the episode's
        coverage in the implementation of this function so that it can be sent
        to the RL agent for reward computation.
        '''
        pass

    @cocotb.coroutine
    @abstractmethod
    def assert_dut_reset_from_rl(self):
        '''
        This coroutine will be called at the start of each RL episode when the
        reset() function of the gym environment is called. It can be used to
        call the assert_reset() coroutine.
        '''
        pass

    @cocotb.coroutine
    @abstractmethod
    def rl_step_dut_tb_configure(self):
        '''
        This coroutine will be called in each step taken by the RL agent. It can
        be used to configure the testbench parameter and dut once the actions for that
        step are obtained from the RL process. 
        
        See the loop in run(self) below for the exact call location. This method 
        must be overridden in the subclass with the core verification logic of 
        the hardware design to be verified.
        '''
        pass

    @cocotb.coroutine
    @abstractmethod
    def rl_step_dut_input_drive(self):
        '''
        This coroutine will be called in each step taken by the RL agent after 
        rl_step_dut_tb_configure(self) coroutine. This completes the DUT input drive
        for one RL step. Coverage tracking also happens parallely and will be sent to
        rl process. With the coverage data, rl agent computes reward.
        
        See the loop in run(self) below for the exact call location. This method 
        must be overridden in the subclass with the core verification logic of 
        the hardware design to be verified.
        '''
        pass

    @abstractmethod
    def rl_step_compute_feedback(self):
        '''
        This function will be called at the end of every RL step to send rl feedback.
        RL observation and RL done signal is computed based on the hardware state and 
        sent to RL process.
        
        See the loop in run(self) below for the exact call location. This method 
        must be overridden in the subclass with the core verification logic of 
        the hardware design to be verified.
        '''
        pass

    @cocotb.coroutine
    @abstractmethod
    def terminate_rl_episode(self):
        '''
        This function will be called at the end of RL episode when rl_done signal is asserted 
        as True from rl_step_compute_feedback(self) function. This asserts end of input drive signals
        to DUT and terminates all the coroutines forked in setup_rl_episode(self) 
        
        See the loop in run(self) below for the exact call location. This method 
        must be overridden in the subclass with the core verification logic of 
        the hardware design to be verified.
        '''
        pass


    def finish_experiment(self):
        '''
        This function will be called at the end of the verification experiment
        after the episode loop is complete. Override this function if necessary
        in the subclass to kill coroutines, close testbench, etc. after the
        verification experiment (see example subclass).
        '''
        pass

    @cocotb.coroutine
    def run(self):
        '''
        This coroutine contains the control flow in the cocotb environment. Do
        not override this in the subclass. Instead, modify the contents of this
        function here if necessary.
        '''

        for i in range(self.NUM_STEPS):
            self.logger.info('cocotb | Waiting for rl step or rl reset ')

            x = self.parent_conn.recv()
            if(x == 'rl_reset'):
                self.logger.info('cocotb | Step ' + str(i + 1))
                setup_rl_episode_coroutine = cocotb.fork(self.setup_rl_episode())
                assert_reset_coroutine = cocotb.fork(self.assert_dut_reset_from_rl())
                yield assert_reset_coroutine.join()
                self.logger.info('cocotb | Waiting for rl step after rl reset ')
                x = self.parent_conn.recv()
                assert x == 'rl_step'

            ''' Receive Action from rl_step '''
            # receive the action from the RL agent
            self.logger.info('cocotb | Waiting for actions from rl step ')
            received_actions = self.parent_conn.recv()
            print("action: ", received_actions)

            # obtain the discrete actions
            num_discrete_params = len(self.DISCRETE_PARAM_VALUES)
            self.discrete_actions.clear()
            for j in range(num_discrete_params):
                # map the interval [0, 1] to the discrete value set linearly
                x = math.ceil(received_actions[j - num_discrete_params] * len(self.DISCRETE_PARAM_VALUES[j]))
                if((x == 0) and (len(self.DISCRETE_PARAM_VALUES[j]) != 0)):
                    x = 1
                self.discrete_actions.append(self.DISCRETE_PARAM_VALUES[j][x - 1])

            # obtain the continous actions
            self.continuous_actions = received_actions[:len(received_actions) - num_discrete_params]
            #assert len(self.continuous_actions) == len(self.FSM_STATES)
            ''' End of computation from rl_step actions '''

            rl_step_dut_tb_configure_coroutine = cocotb.fork(self.rl_step_dut_tb_configure())
            yield rl_step_dut_tb_configure_coroutine.join()

            rl_step_dut_input_drive_coroutine = cocotb.fork(self.rl_step_dut_input_drive())
            yield rl_step_dut_input_drive_coroutine.join()

            self.rl_observation, self.rl_info = self.rl_step_compute_feedback()

            if(self.rl_done):
                terminate_rl_episode_coroutine = cocotb.fork(self.terminate_rl_episode())
                yield terminate_rl_episode_coroutine.join()
                setup_rl_episode_coroutine.kill()

            self.parent_conn.send(self.cocotb_coverage)
            self.parent_conn.send(self.rl_observation)
            self.parent_conn.send(self.rl_done)
            self.parent_conn.send(self.rl_info)

        self.logger.info('cocotb | Waiting for RL process to complete ')

        # end the RL process
        self.rl_process.join()
        self.logger.info('cocotb | RL process joined ')

        self.finish_experiment()
