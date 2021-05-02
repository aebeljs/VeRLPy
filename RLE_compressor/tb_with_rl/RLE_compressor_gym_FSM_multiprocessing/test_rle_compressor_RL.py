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
    timestamp = str(int(time.time()))   # timestamp to tag the log file and model

    config = configparser.ConfigParser()
    config.read('config.ini')

    # set up the logger
    logger = logging.getLogger(__name__)
    for handler in logger.root.handlers[:]:
        logger.root.removeHandler(handler)
    logging.basicConfig(filename=timestamp + '.log',
                        filemode='w',
                        format='%(asctime)s | %(levelname)s | %(message)s',
                        datefmt='%d/%m/%Y %I:%M:%S %p',
                        level=logging.INFO)

    # set up the Pipe and start the RL process
    parent_conn, child_conn = Pipe()
    rl_process = Process(target=RL_run, args=(child_conn, logger, timestamp,))
    rl_process.start()

    # read parameters from config file
    NUM_EPISODES = config['main'].getint('num_episodes')
    FSM_states = ast.literal_eval(config['cocotb']['fsm_states'])
    discrete_params = ast.literal_eval(config['cocotb']['discrete_params'])
    num_discrete_params = len(discrete_params)

    # get the valid value set for each discrete parameter
    discrete_param_values = []
    for param in discrete_params:
        discrete_param_values.append(ast.literal_eval(config['discrete'][param]))

    #######################----user---------##################################
    cocotb.fork(clock_gen(dut.CLK))

    tb = TestBench(dut)
    word_width = 4      # Can be randomised to pick only from the set 1, 2, 4, 8
    tb.word_width = word_width
    #######################----user---------#################################

    for i in range(NUM_EPISODES):
        Z = parent_conn.recv()  # receive the action from the RL agent
        print("action: ", Z)

        discrete_actions = []
        for j in range(num_discrete_params):
            x = math.ceil(Z[j - num_discrete_params] * len(discrete_param_values[j]))
            if((x == 0) and (len(discrete_param_values[j]) != 0)):
                x = 1
            discrete_actions.append(discrete_param_values[j][x - 1])

        Z = Z[:-num_discrete_params]
        assert len(Z) == len(FSM_states)

        #######################----user---------#################################
        count_width = discrete_actions[0]
        print('count width', count_width)
        tb.count_width = count_width

        N = discrete_actions[1]
        print('N =', N)

        cocotb_coverage = []
        m_sig = cocotb.fork(monitor_signals(dut, cocotb_coverage, count_width))   # tracks states covered
        history = ''    # to store the binary sequence for FSM based sequence generation

        # reset the DUT
        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        start_comp = start_compression(tb, word_width, count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # take action
        n = 0
        while(n < N):
            curr_state = get_next_state_of_FSM(history, FSM_states)
            if(dut.RDY_ma_get_input == 1):
                sample = random.random()
                if(sample < Z[curr_state]):
                    input_gen = zero_input_gen(tb)
                    history += '0'
                else:
                    input_gen = random_input_gen(tb)
                    history += '1'
                for t in input_gen:
                    yield tb.input_drv.send(t)
                n = n + 1
                yield RisingEdge(dut.CLK)

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb, 1)
                for t in output_enable:
                    yield tb.input_drv.send(t)

                output_enable = enable_compression_output(tb, 0)
                for t in output_enable:
                    yield tb.input_drv.send(t)

        end_comp = enable_end_compression(tb)
        for t in end_comp:
            yield tb.input_drv.send(t)

        output_enable = enable_compression_output(tb, 1)
        for t in output_enable:
            yield tb.input_drv.send(t)

        for t in range(2):
            yield RisingEdge(dut.CLK)

        output_enable = enable_compression_output(tb, 0)
        for t in output_enable:
            yield tb.input_drv.send(t)

        output_enable = enable_compression_output(tb, 1)
        for t in output_enable:
            yield tb.input_drv.send(t)

        for t in range(2):
            yield RisingEdge(dut.CLK)

        output_enable = enable_compression_output(tb, 0)
        for t in output_enable:
            yield tb.input_drv.send(t)

        for n in range(20):
            yield RisingEdge(dut.CLK)

        yield RisingEdge(dut.CLK)
        
        m_sig.kill()
        # write to a file the coverage, reward, etc.
        logger.info('cocotb | Episode ' + str(i + 1) + ' | history | ' + history)
        #######################----user---------#################################

        parent_conn.send(cocotb_coverage)   # send the coverage to the RL agent

    #######################----user---------#################################
    tb.stop()
    #######################----user---------#################################

    rl_process.join()   #RL process is completed
