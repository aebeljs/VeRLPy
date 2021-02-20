import cocotb
from test_rle_decompression_cocotb import *
import itertools
import matplotlib.pyplot as plt
import sys
from collections import defaultdict

coverage = []
count_width = 4
word_width = 4
random.seed(1)

@coroutine
def monitor_signals(dut):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_count_valid.value == False),
            (int)(dut.rg_word_valid.value == False),
            (int)(dut.rg_counter_valid.value == False),
            (int)(dut.rg_zero_counter.value == 64),
            (int)(dut.rg_word_counter.value == 16),
            (int)(dut.rg_counter.value == 2**count_width - 2),
            (int)(dut.rg_next_count.value != 0),
            (int)(dut.rg_is_next_word.value == True)]
        coverage.append(s)
        ## ** difficult to cover
        ##rg_count_valid == False
        ##rg_word_valid == False
        ##rg_counter_valid == False
        ##rg_zero_counter == 64
        ##rg_word_counter == 16
        ## ** rg_counter == 2**count_width-2
        ## ** rg_next_count != 0
        ##rg_is_next_word == True


@cocotb.test()
def run_test(dut):
    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut))
    tb = Testbench(dut)
    cocotb.fork(get_decompressed_output(dut,tb))

    NUM_EPISODES = 100
    M = 5
    suffix = "_m=" + str(M) + ",numEps=" + str(NUM_EPISODES)
    for n1 in range(NUM_EPISODES):
        print("Episode : ", n1)
        word_width = random.choice([1,2,4,8])
        #word_width = 4
        count_width = random.randint(2,8)
        #count_width = 6

        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        ##Initial compressed input alone will have details of word width and count width
        compressed_input = random.randint(0,2**56 - 1) << 8 | count_width << 4 | word_width
        for n2 in range(M):
            if(dut.RDY_ma_get_inputs != 1):
                yield RisingEdge(dut.RDY_ma_get_inputs)
            yield tb.input_drv.send(InputTransaction(tb,1,compressed_input))
            yield tb.input_drv.send(InputTransaction(tb,0,0))
            ##Input Randomisation
            compressed_input = random.randint(0,2**64-1)
            yield RisingEdge(dut.CLK)
            yield RisingEdge(dut.CLK)

        print("Driven all inputs for this episode ")
        for delay in range(5):
            yield RisingEdge(dut.CLK)
        if(dut.RDY_ma_send_decompressed_output == 1):
            yield FallingEdge(dut.RDY_ma_send_decompressed_output)

        for delay in range(10):
            yield RisingEdge(dut.CLK)

    tb.stop()
    yield RisingEdge(dut.CLK)

    state_list = []
    for cov in coverage:
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
    plt.title("Histogram of covered states\n")
    # plt.savefig('./hist_of_coverage' + suffix + '.png', bbox_inches='tight')
    plt.savefig('./hist_of_coverage' + suffix + '.png', bbox_inches='tight')
    plt.close()
