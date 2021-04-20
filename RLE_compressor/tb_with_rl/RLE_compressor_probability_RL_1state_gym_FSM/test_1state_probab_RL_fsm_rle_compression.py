import cocotb
from test_rle_compression_cocotb import *
from helper import *
from collections import defaultdict
import math

coverage = []
input_tracker = []
cycle_tracker = []
count_width = 0
word_width = 0
random.seed(1)

@cocotb.coroutine
def monitor_signals(dut):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_word_counter.value == 16),
            (int)(dut.rg_zero_counter.value == 64),
            (int)(dut.rg_counter.value == (2**count_width - 2)),
            (int)(dut.rg_next_count != 0),
            # (int)((dut.rg_word_counter.value == 16) and (dut.rg_counter.value == (2**count_width - 2)))]
            (int)((dut.rg_zero_counter.value == 64) and (dut.rg_next_count != 0))]
        s = ''.join(map(str, s))
        coverage.append(s)

@cocotb.test()
def run_test(dut):
    NUM_EPISODES = int(wait_till_read('./RL_output.txt')[0])
    # NUM_EPISODES = 1000
    action_list = []

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

    FSM_states = ['.']
    write_to_file('./cocotb_output.txt', [len(FSM_states)])

    for i in range(NUM_EPISODES):
        print("-----------------------------------------------")
        print("Epsiode number: ", i)

        coverage.clear()
        input_tracker.clear()
        cycle_tracker.clear()
        history = ''

        # get action
        print('waiting for RL action', i)
        Z = wait_till_read('./RL_output.txt')
        # Z = ['0.512462424523714', '0.9434345122764985', '1.0']
        print("action: ", Z)
        Z = [float(i) for i in Z]


        ##############################################
        # comment this block if design config params are not in action space
        count_width = math.ceil(Z[-2] * 8)
        if(count_width==0):
            count_width = 1
        print('count width', count_width)
        tb.count_width = count_width

        N = math.ceil(Z[-1] * 10) # total number of elements in activation map
        if(N == 0):
            N += 1
        N *= 100
        print('N =', N)

        Z = Z[:-2]
        ##############################################

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
            # print('knob', curr_state)
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
        write_to_file('./cocotb_output.txt', coverage)

    tb.stop()
