import cocotb
from test_rle_decompression_cocotb import *
import itertools
import matplotlib.pyplot as plt
import sys
from collections import defaultdict

coverage = []
total_binary_coverage = [0] * 8
total_set_coverage = []
total_coverage = []
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

    NUM_EPISODES = 500
    activation_map = []
    input_list = []
    word_list = []
    count_list = []
    compressed_list = []
    N = 400
    M = 5

    word_width = 4
    count_width = 6

    # suffix = "_m=" + str(M) + ",numEps=" + str(NUM_EPISODES)
    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + str(word_width) + ',count_width=' + str(count_width)
    for n1 in range(NUM_EPISODES):
        print("Episode : ", n1)
        # word_width = random.choice([1,2,4,8])
        #word_width = 4
        # count_width = random.randint(2,8)
        #count_width = 6

        coverage.clear()
        activation_map.clear()
        input_list.clear()

        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        Pr_zero = (int)(random.random() * 100) / 100. # get probability value from [0.01,0.02,...,0.99]
        #Pr_zero = 0.57
        print('Probab:', Pr_zero)

        design_config_string = count_width << 4 | word_width

        for n2 in range(N):
            if(random.random() < Pr_zero):
                # next element is 0
                activation_map.append(0)
            else:
                # next element is not 0
                activation_map.append(random.randint(1, 2**(word_width*4)))

        # print(activation_map)
        # break

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
        # print(input_list)
        input_list.insert(0, input_list.pop(first_compressed_zero_idx))
        print(input_list)

        ##Initial compressed input alone will have details of word width and count width
        # input_list = [13908259987590759268, 5466339630142750055, 7708008654023722417, 13711433221677006084, 4791302593951332211, 297309096011432976, 12804395393502841569, 17160679680036653830, 3696519104342578997, 2325550866100392001, 17597997525760624910, 5843402158363911501, 17183764384036183007, 4829002859638981380, 8450570782378548667, 557071639388608969, 297522366668538896, 11045939112885484732, 13137551342047707595, 15582317614200405168, 3477069253226807425, 5742721319435764721, 4284827710540203280, 2603391325574209430, 145294693537693956, 11380606908143380531, 17972173053635191860, 581036954334987297, 9376578776570838914, 2255091308962467159, 6672892889147781230, 1207250718181834817, 3287439725080637815, 18268255891619857001, 1915831582312376255, 1161638398935816]
        # input_list = [9368631043577398116, 2216776977775572170, 14301683823907461990, 15121658413985603301, 11948213363879247217, 581257939524850704, 2183256803474030594, 9779846399426106866, 268734901004314769, 2360453622603452609, 17384146028894171654, 5107697065764309873, 7179854534921886875, 4684889037429817604, 16462430396108157943, 12153119009882216616, 293099065720318992, 18093367915201532687, 15838585278011049037, 10053140081791194139, 4629986359788179714, 17202326133095786986, 7074750978420750278, 11019334811863768481, 4687191977688581892, 4164206021795012246, 2249524958253636221, 585614273313575968, 14403408446759471993, 2756744041155459975, 9012741384553755700, 1171516520468320450, 16532561956772814059, 147720, 2699922016]
        n2 = 1
        compressed_input = input_list[0]
        while n2 < len(input_list):
            if(dut.RDY_ma_get_inputs != 1):
                yield RisingEdge(dut.CLK)
            else:
                print(" Compressed input : ",n1,n2)
                yield tb.input_drv.send(InputTransaction(tb,1,compressed_input))
                yield tb.input_drv.send(InputTransaction(tb,0,0))
                ##Input Randomisation
                compressed_input = input_list[n2]
                for delay in range(2):
                    yield RisingEdge(dut.CLK)
                n2=n2+1

        print("Driven all inputs for this episode ")
        for delay in range(5):
            yield RisingEdge(dut.CLK)
        if(dut.RDY_ma_send_decompressed_output == 1):
            yield FallingEdge(dut.RDY_ma_send_decompressed_output)

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        print(tb.expected_output.count)
        print(tb.expected_output)
        print(tb.got_output.count)
        print(tb.got_output)
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
        total_coverage.extend(coverage)
        set_coverage = list(set(coverage))
        print('set coverage:', set_coverage)
        total_set_coverage.extend(set_coverage)
        for item in coverage:
            for k in range(len(item)):
                total_binary_coverage[k] += (int)(item[k])


    tb.stop()
    yield RisingEdge(dut.CLK)

    total_coverage.sort()
    from collections import Counter
    labels = list(Counter(total_coverage).keys()) # equals to list(set(words))
    counts = list(Counter(total_coverage).values()) # counts the elements' frequency
    print('Coverage histogram')
    for c in range(len(labels)):
        print(labels[c], counts[c])

    plt.vlines(labels, 0, counts, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of covered states\n")
    plt.savefig('./hist_of_coverage' + suffix + '.png', bbox_inches='tight')
    plt.close()

    print(total_binary_coverage)
    plt.vlines(list(range(8)), 0, total_binary_coverage, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of binary coverage\n")
    plt.savefig('./hist_of_binary_coverage' + suffix + '.png', bbox_inches='tight')
    plt.close()

    total_set_coverage.sort()
    labels = list(Counter(total_set_coverage).keys()) # equals to list(set(words))
    counts = list(Counter(total_set_coverage).values()) # counts the elements' frequency
    print('Set coverage histogram')
    for c in range(len(labels)):
        print(labels[c], counts[c])
    plt.vlines(labels, 0, counts, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of set of covered states\n")
    plt.savefig('./hist_of_set_coverage' + suffix + '.png', bbox_inches='tight')
    plt.close()
