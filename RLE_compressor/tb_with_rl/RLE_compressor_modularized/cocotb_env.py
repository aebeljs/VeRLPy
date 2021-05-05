from abc import ABC, abstractmethod

import cocotb
from test_rle_compressor_cocotb import *
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
        self.timestamp = str(int(time.time()))   # timestamp to tag the log file and model

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        # set up the logger
        self.logger = logging.getLogger(__name__)
        # for handler in self.logger.root.handlers[:]:
        #     self.logger.root.removeHandler(handler)
        logging.basicConfig(filename=self.timestamp + '.log',
                            filemode='w',
                            format='%(asctime)s | %(levelname)s | %(message)s',
                            datefmt='%d/%m/%Y %I:%M:%S %p',
                            level=logging.INFO)

        # set up the Pipe and start the RL process
        self.parent_conn, child_conn = Pipe()
        self.rl_process = Process(target=RL_run, args=(child_conn, self.logger, self.timestamp,))
        self.rl_process.start()

        # read parameters from config file
        self.NUM_EPISODES = self.config['main'].getint('num_episodes')
        self.FSM_states = ast.literal_eval(self.config['cocotb']['fsm_states'])
        discrete_params = ast.literal_eval(self.config['cocotb']['discrete_params'])

        # get the valid value set for each discrete parameter
        self.discrete_param_values = []
        for param in discrete_params:
            self.discrete_param_values.append(ast.literal_eval(self.config['discrete'][param]))
        self.cocotb_coverage = []
        self.discrete_actions = []
        self.continuous_actions = []

    @abstractmethod
    def setup_experiment(self):
        pass

    @abstractmethod
    def take_step(self):
        pass

    @abstractmethod
    def finish_experiment(self):
        pass

    def run(self):
        print('test', self.NUM_EPISODES)
        self.setup_experiment()

        for i in range(self.NUM_EPISODES):
            self.continuous_actions = self.parent_conn.recv()  # receive the action from the RL agent
            print("action: ", self.continuous_actions)

            num_discrete_params = len(self.discrete_param_values)
            self.discrete_actions.clear()
            for j in range(num_discrete_params):
                x = math.ceil(self.continuous_actions[j - num_discrete_params] * len(self.discrete_param_values[j]))
                if((x == 0) and (len(self.discrete_param_values[j]) != 0)):
                    x = 1
                self.discrete_actions.append(self.discrete_param_values[j][x - 1])

            self.continuous_actions = self.continuous_actions[:-num_discrete_params]
            assert len(self.continuous_actions) == len(self.FSM_states)
            #######################----user---------#################################
            self.take_step()
            #######################----user---------#################################
            self.parent_conn.send(self.cocotb_coverage)   # send the coverage to the RL agent

        self.rl_process.join()
        self.finish_experiment()
