import cocotb
from test_rle_decompression_cocotb import *
from helper import *

coverage = []
count_width = 6
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
        s = ''.join(map(str, s))
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

    NUM_EPISODES = int(wait_till_read('./RL_output.txt')[0])
    activation_map = []
    input_list = []
    word_list = []
    count_list = []
    compressed_list = []
    N = 400
    M = 5

    word_width = 4
    count_width = 6

    FSM_states = ['.']
    write_to_file('./cocotb_output.txt', [len(FSM_states)])

    # suffix = "_m=" + str(M) + ",numEps=" + str(NUM_EPISODES)
    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + str(word_width) + ',count_width=' + str(count_width)
    for n1 in range(NUM_EPISODES):
        print('------------------------')
        print("Episode : ", n1)
        # word_width = random.choice([1,2,4,8])
        #word_width = 4
        # count_width = random.randint(2,8)
        #count_width = 6

        coverage.clear()
        activation_map.clear()
        input_list.clear()
        history = ''

        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        print('waiting for RL action', n1)
        Pr_zero = wait_till_read('./RL_output.txt')
        # Pr_zero = (int)(random.random() * 100) / 100. # get probability value from [0.01,0.02,...,0.99]
        print('Probab:', Pr_zero)
        Pr_zero = [float(i) for i in Pr_zero]

        design_config_string = count_width << 4 | word_width

        for n2 in range(N):
            curr_state = match(FSM_states, history)
            if(random.random() < Pr_zero[curr_state]):
                # next element is 0
                activation_map.append(0)
                history += '0'
            else:
                # next element is not 0
                activation_map.append(random.randint(1, 2**(word_width*4)))
                history += '1'

        # print(activation_map)

        count_overflow_tracker = 8 # initially least significant 8 bits are for design config
        word_overflow_tracker = 0
        compressed_zero_vec = design_config_string # LSB is made as the design config params
        compressed_word_vec = 0
        zero_count = 0
        first_compressed_zero_idx = -1 # to store the index of the first 64 bit number denoting zero count
        for element in activation_map:
            if(element == 0):
                zero_count += 1 # count consecutive 0s
            else:
                while(zero_count >= 2**count_width - 1):
                    if(count_overflow_tracker + count_width < 64): # there is still room inside the 64 bits
                        compressed_zero_vec = compressed_zero_vec | ((2**count_width - 1) << count_overflow_tracker)
                        count_overflow_tracker += count_width
                        zero_count -= (2**count_width - 2)
                    else: # need to move some bits of the current count to the next compressed word
                        compressed_zero_vec = compressed_zero_vec | (((2**count_width - 1) << count_overflow_tracker) & 0xFFFFFFFFFFFFFFFF)
                        if(first_compressed_zero_idx == -1):
                            first_compressed_zero_idx = len(input_list) # mark the position of first compressed zero count vector
                        input_list.append(compressed_zero_vec) # add the compressed zero count vector to the list
                        compressed_zero_vec = (2**count_width - 1) >> (64 - count_overflow_tracker) # make the new compressed zero vector with the remaining bits
                        count_overflow_tracker += count_width
                        count_overflow_tracker %= 64 # reset the overflow tracker
                        zero_count -= (2**count_width - 2)

                if(zero_count > 0):
                    if(count_overflow_tracker + count_width < 64): # there is still room inside the 64 bits
                        compressed_zero_vec = compressed_zero_vec | (zero_count << count_overflow_tracker)
                        count_overflow_tracker += count_width
                        zero_count = 0 # all 0s upto this point accounted correctly now
                        compressed_word_vec = compressed_word_vec | ((element << word_overflow_tracker) & 0xFFFFFFFFFFFFFFFF) # add the word to the compressed word vec
                        word_overflow_tracker += (word_width * 4) # no issues here since all possible word_width values is a factor of 64
                        if(word_overflow_tracker == 64): # compressed word vector full
                            input_list.append(compressed_word_vec)
                            if(len(str(bin(compressed_word_vec))[2:]) > 64):
                                print("word overflow")
                            word_overflow_tracker = 0
                            compressed_word_vec = 0
                    else: # need to move some bits of the current count to the next compressed word
                        compressed_zero_vec = compressed_zero_vec | ((zero_count << count_overflow_tracker) & 0xFFFFFFFFFFFFFFFF)
                        if(first_compressed_zero_idx == -1):
                            first_compressed_zero_idx = len(input_list)
                        input_list.append(compressed_zero_vec)
                        compressed_zero_vec = zero_count >> (64 - count_overflow_tracker)
                        count_overflow_tracker += count_width
                        count_overflow_tracker %= 64
                        zero_count = 0
                        compressed_word_vec = compressed_word_vec | ((element << word_overflow_tracker) & 0xFFFFFFFFFFFFFFFF)
                        word_overflow_tracker += (word_width * 4)
                        if(word_overflow_tracker == 64):
                            input_list.append(compressed_word_vec)
                            word_overflow_tracker = 0
                            compressed_word_vec = 0

        if(count_overflow_tracker != 0): # final compressed zero vector that did not overflow yet
            if(first_compressed_zero_idx == -1):
                first_compressed_zero_idx = len(input_list)
            input_list.append(compressed_zero_vec)
        if(word_overflow_tracker != 0): # final compressed word vector that did not overflow yet
            input_list.append(compressed_word_vec)
        input_list.insert(0, input_list.pop(first_compressed_zero_idx))
        # print(input_list)

        ##Initial compressed input alone will have details of word width and count width
        n2 = 0
        while n2 < len(input_list):
            if(dut.RDY_ma_get_inputs != 1):
                yield RisingEdge(dut.CLK)
            else:
                # print(" Compressed input : ",n1,n2)
                yield tb.input_drv.send(InputTransaction(tb,1,input_list[n2]))
                yield tb.input_drv.send(InputTransaction(tb,0,0))
                for delay in range(2):
                    yield RisingEdge(dut.CLK)
                n2 += 1

        print("Driven all inputs for this episode ")
        for delay in range(5):
            yield RisingEdge(dut.CLK)
        if(dut.RDY_ma_send_decompressed_output == 1):
            yield FallingEdge(dut.RDY_ma_send_decompressed_output)

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        # print(tb.expected_output.count)
        # print(tb.expected_output)
        # print(tb.got_output.count)
        # print(tb.got_output)
        tb.compare_outputs()
        print('Outputs compared')
        tb.start_decompression=1
        tb.next_count=0
        tb.next_word=0
        tb.cont_count=0

        tb.decompress_word=0
        tb.compressed_word=0
        tb.compressed_count=0
        tb.zero_counter=64
        tb.word_counter=64
        tb.counter=0
        tb.count_valid=0

        # process coverage of this episode here

        # write to a file the coverage, reward, etc.
        write_to_file('./cocotb_output.txt', coverage)

    tb.stop()
