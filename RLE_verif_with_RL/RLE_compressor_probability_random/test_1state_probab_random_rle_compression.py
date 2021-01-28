import cocotb
from test_rle_compression_cocotb import *
import itertools
import matplotlib.pyplot as plt
import sys

coverage = []

@cocotb.coroutine
def monitor_signals(dut):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_word_counter.value == 16),
            (int)(dut.rg_zero_counter.value == 64),
            (int)(dut.rg_counter.value == (2**count_width - 2)),
            (int)(dut.rg_next_count != 0)]
        coverage.append(s)

@cocotb.test()
def run_test(dut):
    NUM_EPISODES = 100
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

    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ",word_w=" + str(word_width) + ",count_w=" + str(count_width)

    tb = TestBench(dut)
    tb.word_width = word_width
    tb.count_width = count_width

    for i in range(NUM_EPISODES):
        print("-----------------------------------------------")
        print("Epsiode number: ", i)

        # reset the DUT
        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        coverage.clear()

        start_comp = start_compression(tb,word_width,count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # get action
        Z = (int)(random.random() * 100) / 100.
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

        '''
        output_enable = enable_compression_output(tb,1)
        for t in output_enable:
            yield tb.input_drv.send(t)
        end_comp = enable_end_compression(tb)
        for t in end_comp:
            yield tb.input_drv.send(t)
        '''
        for n in range(20):
            yield RisingEdge(dut.CLK)

        yield RisingEdge(dut.CLK)


        # calculate the reward
        coverage.sort()
        # set_coverage has the set of states covered
        set_coverage = list(coverage for coverage,_ in itertools.groupby(coverage))
        coverage_list = coverage_list + set_coverage
        print("i = ", i)
        print("last coverage: ", set_coverage)

    tb.stop()

    # plot results
    plt.hist(chosen_actions)
    plt.title("Stochastic input - Histogram of probability of zero in the activation map\n")
    plt.tight_layout()
    plt.savefig('./new_hist_of_actions' + suffix + '.png')
    plt.close()

    state_list = []
    for cov in coverage_list:
        x = ''.join(map(str, cov))
        state_list.append(x)

    state_list.sort()
    from collections import Counter
    labels = Counter(state_list).keys() # equals to list(set(words))
    counts = Counter(state_list).values() # counts the elements' frequency
    plt.vlines(labels, 0, counts, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    # plt.hist(state_list)
    plt.title("Stochastic input - Histogram of covered states\n")
    plt.savefig('./new_hist_of_coverage' + suffix + '.png')
    plt.close()
