import cocotb
from test_rle_compressor_cocotb import *
from RL_helper import *
from multiprocessing import *
import numpy as np
import configparser, ast, logging, math, time

cocotb_coverage = []
count_width = 6
word_width = 4

@cocotb.coroutine
def monitor_signals(dut):
    global count_width
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
    timestamp = str(int(time.time()))

    config = configparser.ConfigParser()
    config.read('config.ini')

    logger = logging.getLogger(__name__)
    for handler in logger.root.handlers[:]:
        logger.root.removeHandler(handler)
    logging.basicConfig(filename=timestamp + '.log',
                                filemode='w',
                                format='%(asctime)s | %(levelname)s | %(message)s',
                                datefmt='%d/%m/%Y %I:%M:%S %p',
                                level=logging.INFO)

    parent_conn, child_conn = Pipe()
    rl_process = Process(target=rl_run, args=(child_conn, logger, timestamp,))
    rl_process.start()

    NUM_EPISODES = config['main'].getint('num_episodes')

    global word_width
    global count_width

    word_width = 4 #Can be randomised to pick only from the set 1, 2, 4, 8
    count_width = 6 # count_width = random.randint(1,8)

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut)) # tracks states covered

    tb = TestBench(dut)
    tb.word_width = word_width
    tb.count_width = count_width

    N = 400

    FSM_states = ast.literal_eval(config['cocotb']['fsm_states'])
    discrete_params = ast.literal_eval(config['cocotb']['discrete_params'])
    num_discrete_params = len(discrete_params)
    discrete_param_values = []
    for param in discrete_params:
        discrete_param_values.append(ast.literal_eval(config['discrete'][param]))

    for i in range(NUM_EPISODES):
        print("-----------------------------------------------")
        print("Epsiode number: ", i)

        cocotb_coverage.clear()
        history = ''

        # get action
        print('waiting for RL action', i)
        Z = parent_conn.recv()
        print("action: ", Z)
        logger.info('cocotb | Episode ' + str(i + 1) + ' | action | ' + str(Z))

        discrete_actions = []
        for j in range(num_discrete_params):
            x = math.ceil(Z[j - num_discrete_params] * len(discrete_param_values[j]))
            if((x == 0) and (len(discrete_param_values[j]) != 0)):
                x = 1
            discrete_actions.append(discrete_param_values[j][x - 1])

        count_width = discrete_actions[0]
        print('count width', count_width)
        tb.count_width = count_width

        N = discrete_actions[1]
        print('N =', N)

        Z = Z[:-num_discrete_params]

        assert len(Z) == len(FSM_states)

        # reset the DUT
        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        start_comp = start_compression(tb,word_width,count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # take action
        n = 0
        while(n < N):
            curr_state = match(FSM_states, history)
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
                n=n+1
                yield RisingEdge(dut.CLK)

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb,1)
                for t in output_enable:
                    yield tb.input_drv.send(t)

                output_enable = enable_compression_output(tb,0)
                for t in output_enable:
                    yield tb.input_drv.send(t)

        end_comp = enable_end_compression(tb)
        for t in end_comp:
            yield tb.input_drv.send(t)

        output_enable = enable_compression_output(tb,1)
        for t in output_enable:
            yield tb.input_drv.send(t)

        for t in range(2):
            yield RisingEdge(dut.CLK)

        output_enable = enable_compression_output(tb,0)
        for t in output_enable:
            yield tb.input_drv.send(t)

        output_enable = enable_compression_output(tb,1)
        for t in output_enable:
            yield tb.input_drv.send(t)

        for t in range(2):
            yield RisingEdge(dut.CLK)

        output_enable = enable_compression_output(tb,0)
        for t in output_enable:
            yield tb.input_drv.send(t)

        for n in range(20):
            yield RisingEdge(dut.CLK)

        yield RisingEdge(dut.CLK)

        # write to a file the coverage, reward, etc.
        logger.info('cocotb | Episode ' + str(i + 1) + ' | history | ' + history)
        parent_conn.send(cocotb_coverage)

    rl_process.join()
    tb.stop()
