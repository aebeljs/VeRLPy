import cocotb
from test_rle_compression_cocotb import *
from helper import *
from collections import defaultdict

coverage = []
value_coverage = []
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
            (int)(dut.rg_next_count != 0),
            (int)((dut.rg_word_counter.value == 16) and (dut.rg_counter.value == (2**count_width - 2)))]
        s = ''.join(map(str, s))
        t = [hex(dut.rg_word_counter.value),
            hex(dut.rg_zero_counter.value),
            hex(dut.rg_counter.value == (2**count_width - 2)),
            hex(dut.rg_next_count != 0)]
        coverage.append(s)
        value_coverage.append(t)
        if(DEBUG_LOG):
            cycle_tracker.append((int)(dut.EN_ma_get_input.value))
            input_tracker.append((hex)(dut.ma_get_input_val.value))

@cocotb.test()
def run_test(dut):
    # NUM_EPISODES = 1000
    NUM_EPISODES = int(wait_till_read('./RL_output.txt')[0])
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

    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ",word_w=" + str(word_width) + ",count_w=" + str(count_width)

    tb = TestBench(dut)
    tb.word_width = word_width
    tb.count_width = count_width

    FSM_states = ['00', '01', '10', '11']

    write_to_file('./cocotb_output.txt', [len(FSM_states)])

    if(DEBUG_LOG):
        state_tracker_dict = {}
        state_tracker_dict = defaultdict(lambda:set([]), state_tracker_dict)
        log_filename = './log' + suffix + '.txt'
        f = open(log_filename, 'a+')

    # log_file = open("Log_file.txt", "w")
    for i in range(NUM_EPISODES):
        print("-----------------------------------------------")
        print("Epsiode number: ", i)

        # reset the DUT
        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        coverage.clear()
        value_coverage.clear()
        input_tracker.clear()
        cycle_tracker.clear()
        history = ''

        start_comp = start_compression(tb,word_width,count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # get action
        print('waiting for RL action', i)
        Z = wait_till_read('./RL_output.txt')
        print("action: ", Z)
        Z = [float(i) for i in Z]

        # activation_map = [1]
        # for j in range(39):
        #     activation_map.append(0)
        # activation_map = activation_map * 8
        # activation_map.append(1)
        # for j in range(10):
        #     activation_map.append(0)
        # activation_map.append(1)
        # for j in range(63):
        #     activation_map.append(0)
        # activation_map.append(1)
        # for j in range(4):
        #     activation_map.append(0)
        #
        # n = 0
        # while(n < N):
        #     if(dut.RDY_ma_get_input == 1):
        #         input_gen = specific_input_gen(tb, activation_map[n])
        #         history += str(activation_map[n])
        #         for t in input_gen:
        #             yield tb.input_drv.send(t)
        #         n=n+1
        #         yield RisingEdge(dut.CLK)
        #
        #     elif(dut.RDY_mav_send_compressed_value == 1):
        #         output_enable = enable_compression_output(tb,1)
        #         for t in output_enable:
        #             yield tb.input_drv.send(t)
        #
        #         output_enable = enable_compression_output(tb,0)
        #         for t in output_enable:
        #             yield tb.input_drv.send(t)


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

        if(DEBUG_LOG):
            log_episode(f, i+1, Z, coverage, input_tracker, cycle_tracker, state_tracker_dict)

        # write to a file the coverage, reward, etc.
        write_to_file('./cocotb_output.txt', coverage)
        # log_file.write('Episode ' + str(i+1) + '\n')
        # log_file.write(history + '\n')
        # for x in coverage:
        #     log_file.write(x + ' ')
        # log_file.write('\n')
        # for x in value_coverage:
        #     log_file.write(' '.join(x) + '\n')
        # log_file.write('\n')
        # print(history)

    # log_file.close()
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
