import cocotb
from test_rle_compression_cocotb import *
import itertools
import matplotlib.pyplot as plt

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
    NUM_EPISODES = 1000
    action_list = []

    N = 400 # total number of elements in activation map
    I = 100 # change this later

    for i in range(N - I):
        action_list.append(i)

    global word_width
    global count_width

    word_width = 4 #Can be randomised to pick only from the set 1, 2, 4, 8
    count_width = 6 # count_width = random.randint(1,8)

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut)) # tracks states covered

    chosen_actions = []
    coverage_list = []

    suffix = "_N=" + str(N) + ",I=" + str(I) + ",numEps=" + str(NUM_EPISODES) + ",word_w=" + str(word_width) + ",count_w=" + str(count_width)

    tb = TestBench(dut)
    for i in range(NUM_EPISODES):
        print("Epsiode number: ", i)

        # take step
        # action_taken, next_state, reward = take_step_in_env(curr_state, dut)
        # wrap this one episode inside the training loop

        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        # print("coverage len", len(coverage))
        #coverage.clear()

        coverage.clear()
        tb.word_width = word_width
        tb.count_width = count_width
        start_comp = start_compression(tb,word_width,count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # generate action for agent based on curr_state
        Z =  random.choice(action_list)

        chosen_actions.append(Z)
        print("action: ", Z)

        # take action
        # number of non-zero activation map elements at the start
        n = 0
        while(n < I):
            if(dut.RDY_ma_get_input == 1):
                input_gen = random_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                n=n+1
                yield RisingEdge(dut.CLK)

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb,0)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                #n = n-1 Enabling output is not considered as new input

        # RL generated number of consecutive 0s
        n=0
        while(n < Z):
            # generate consecutive 0s
            if(dut.RDY_ma_get_input == 1):
                input_gen = zero_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                n=n+1
                yield RisingEdge(dut.CLK)

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb,0)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                #n = n-1 Enabling output is not considered as new input

        # remaining non-zero elements in the activation map
        n=0
        while( n < N - Z - I):
            if(dut.RDY_ma_get_input == 1):
                input_gen = random_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                n = n + 1
                yield RisingEdge(dut.CLK)

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb,0)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                #n = n-1  Enabling output is not considered as new input

        end_comp = enable_end_compression(tb,1)
        for t in end_comp:
            yield tb.input_drv.send(t)
        
        output_enable = enable_compression_output(tb,1)
        for t in output_enable:
            yield tb.input_drv.send(t)

        output_enable = enable_compression_output(tb,1)
        for t in output_enable:
            yield tb.input_drv.send(t)

        output_enable = enable_compression_output(tb,1)
        for t in output_enable:
            yield tb.input_drv.send(t)

        end_comp = enable_end_compression(tb,0)
        for t in end_comp:
            yield tb.input_drv.send(t)

        for n in range(20):
            yield RisingEdge(dut.CLK)

        yield RisingEdge(dut.CLK)


        # calculate the reward
        coverage.sort()
        set_coverage = list(coverage for coverage,_ in itertools.groupby(coverage))
        print("last coverage: ", set_coverage)
        coverage_list = coverage_list + set_coverage

    tb.stop()
    # plot results
    plt.hist(chosen_actions)
    plt.title("Random choice - Histogram of consecutive zeros in the activation map")
    plt.savefig('./hist_of_actions' + suffix + '.png')
    plt.close()

    state_list = []
    for cov in coverage_list:
        x = ''.join(map(str, cov))
        state_list.append(x)

    plt.hist(state_list)
    plt.title("Random choice - Histogram of covered states")
    plt.savefig('./hist_of_coverage' + suffix + '.png')
    plt.close()
