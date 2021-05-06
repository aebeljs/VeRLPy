from abc import ABC, abstractmethod
import cocotb
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
        self.NUM_EPISODES = self.config['main'].getint('num_episodes')
        self.FSM_STATES = ast.literal_eval(self.config['cocotb']['fsm_states'])

        # get the valid value set for each discrete parameter
        discrete_params = ast.literal_eval(self.config['cocotb']['discrete_params'])
        self.DISCRETE_PARAM_VALUES = []
        for param in discrete_params:
            self.DISCRETE_PARAM_VALUES.append(ast.literal_eval(self.config['discrete'][param]))

        self.cocotb_coverage = []   # list to be populated with each episode's coverage
        self.discrete_actions = []  # list which will have the discrete actions in each episode
        self.continuous_actions = []    # list which will have the continuous actions in each episode

    def setup_experiment(self):
        '''
        This function will be called before the verification loop is started in
        run(self). Override this function if necessary in the subclass to set
        up coroutines like clock signal before the start of the
        verification (see example subclass).
        '''
        pass

    @cocotb.coroutine
    @abstractmethod
    def verify(self):
        '''
        This coroutine will be called in each episode of the core verification
        loop once the actions for that episode are obtained from the RL process.
        See the loop in run(self) below for the exact call location. This method
        must be overridden in the subclass with the core verification logic for
        hardware design to be verified.
        
        The list self.cocotb_coverage must be populated with the episode's
        coverage in the implementation of this function so that it can be sent
        to the RL agent for reward computation.
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
        self.setup_experiment()

        # verification loop
        for i in range(self.NUM_EPISODES):
            self.logger.info('cocotb | Episode ' + str(i + 1))

            # receive the action from the RL agent
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
            self.continuous_actions = received_actions[:-num_discrete_params]
            assert len(self.continuous_actions) == len(self.FSM_STATES)

            # execute the verification logic of the design
            verif_coroutine = cocotb.fork(self.verify())
            yield verif_coroutine.join()

            # send the coverage to the RL agent for computing reward
            self.parent_conn.send(self.cocotb_coverage)

        # end the RL process
        self.rl_process.join()

        self.finish_experiment()
