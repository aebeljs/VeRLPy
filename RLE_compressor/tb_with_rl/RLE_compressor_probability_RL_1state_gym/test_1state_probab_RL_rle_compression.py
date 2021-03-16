import cocotb
from test_rle_compression_cocotb import *
import itertools
import matplotlib.pyplot as plt
import sys
import os
import fcntl
from collections import defaultdict

coverage = []
input_tracker = []
cycle_tracker = []
random.seed(1)

@cocotb.coroutine
def monitor_signals(dut):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_word_counter.value == 16),
            (int)(dut.rg_zero_counter.value == 64),
            (int)(dut.rg_counter.value == (2**count_width - 2)),
            (int)(dut.rg_next_count != 0)]
        s = ''.join(map(str, s))
        coverage.append(s)
        if(DEBUG_LOG):
            cycle_tracker.append((int)(dut.EN_ma_get_input.value))
            input_tracker.append((hex)(dut.ma_get_input_val.value))

@cocotb.test()
def run_test(dut):
    NUM_EPISODES = 1000
    global DEBUG_LOG
    DEBUG_LOG = False
    action_list = []

    N = 400 # total number of elements in activation map

    global word_width
    global count_width

    word_width = 4 #Can be randomised to pick only from the set 1, 2, 4, 8
    count_width = 6 # count_width = random.randint(1,8)

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut)) # tracks states covered

    chosen_actions = []
    coverage_list = []
    total_binary_coverage = [0] * 4

    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ",word_w=" + str(word_width) + ",count_w=" + str(count_width)

    tb = TestBench(dut)
    tb.word_width = word_width
    tb.count_width = count_width

    if(DEBUG_LOG):
        state_tracker_dict = {}
        state_tracker_dict = defaultdict(lambda:set([]), state_tracker_dict)
        log_filename = './log' + suffix + '.txt'
        f = open(log_filename, 'a+')

    for i in range(NUM_EPISODES):
        print("-----------------------------------------------")
        print("Epsiode number: ", i)

        # reset the DUT
        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        coverage.clear()
        input_tracker.clear()
        cycle_tracker.clear()

        start_comp = start_compression(tb,word_width,count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # get action
        print('waiting for RL action')
        Z = float(wait_till_read('./RL_output.txt'))
        print("action: ", Z)

        chosen_actions.append(Z)

        # take action
        n = 0
        while(n < N):
            if(dut.RDY_ma_get_input == 1):
                sample = random.random()
                if(sample < Z):
                    input_gen = zero_input_gen(tb)
                else:
                    input_gen = random_input_gen(tb)
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

        if(DEBUG_LOG):
            log_episode(f, i+1, Z, coverage, input_tracker, cycle_tracker, state_tracker_dict)

        # write to a file the coverage, reward, etc.
        write_to_file('./cocotb_output.txt', coverage)


    tb.stop()

def log_episode(file, episode, action, coverage_vec_seq, map_val_seq, cycle_vec_seq, dict):
    file.write('Episode ' + str(episode) + '\n')
    file.write('Action ' + str(action) + '\n')
    state_list = []
    for cov in coverage_vec_seq:
        x = ''.join(map(str, cov))
        state_list.append(x)
    n = len(coverage_vec_seq)
    assert(n == len(map_val_seq))
    assert(n == len(cycle_vec_seq))
    for ii in range(n):
        file.write('(' + state_list[ii] + ',' + str(map_val_seq[ii]) + ',' + str(cycle_vec_seq[ii]) + ') ')
        dict[state_list[ii]].add(action)
    file.write('\n')

def log_aggregate(file, dict):
    print(dict, file=file)

def wait_till_read(filename):
    while(True):
        # keep looping this
        if(os.path.isfile(filename)):
            with open(filename, "r+") as f:
                fcntl.flock(f, fcntl.LOCK_EX) # lock to avoid concurrency issues
                x = f.readline()
                if(len(x) != 0):
                    # RL has output something
                    f.truncate(0)
                    fcntl.flock(f, fcntl.LOCK_UN)
                    f.close()
                    break
                fcntl.flock(f, fcntl.LOCK_UN)
                f.close()
    return x

def write_to_file(filename, cov):
    with open(filename, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX) # lock to avoid concurrency issues
        for x in cov:
            f.write(x + '\n')
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()
        print('coverage of size', len(cov), 'written')
