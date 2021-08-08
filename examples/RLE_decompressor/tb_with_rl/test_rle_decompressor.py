import cocotb
from verlpy import CocotbEnv, utils
from test_rle_decompressor_helper import Testbench, InputTransaction, get_decompressed_output
from cocotb.triggers import Timer, RisingEdge, FallingEdge
import random
import gym

class RLEDecompressorCocotbEnv(CocotbEnv):
    def __init__(self, dut, observation_space):
        super().__init__()
        self.dut = dut
        self.tb = Testbench(dut)
        self.observation_space = observation_space
        self.activation_map = []
        self.input_list = []
        self.history = ''

    @cocotb.coroutine
    def setup_rl_episode(self):
        self.cocotb_coverage.clear()
        self.activation_map.clear()
        self.input_list.clear()
        self.history = ''
        self.N = 400
        self.count_width = 6
        self.word_width = 4
        self.clock_coroutine = cocotb.fork(self.clock_gen(self.dut.CLK, 1))
        self.coverage_coroutine = cocotb.fork(monitor_signals(self.dut, self.cocotb_coverage, self.count_width))
        self.get_output_coroutine = cocotb.fork(get_decompressed_output(self.dut, self.tb))
        yield Timer(1)
        yield self.assert_reset(self.dut.RST_N, 0, 1, 2)

    @cocotb.coroutine
    def rl_step(self):
        for delay in range(10):
            yield RisingEdge(self.dut.CLK)

        design_config_string = self.count_width << 4 | self.word_width

        for n2 in range(self.N):
            curr_state = utils.get_next_state_of_FSM(self.history, self.FSM_STATES)
            if(random.random() < self.continuous_actions[curr_state]):
                # next element is 0
                self.activation_map.append(0)
                self.history += '0'
            else:
                # next element is not 0
                self.activation_map.append(random.randint(1, 2**(self.word_width*4)))
                self.history += '1'

        count_overflow_tracker = 8 # initially least significant 8 bits are for design config
        word_overflow_tracker = 0
        compressed_zero_vec = design_config_string # LSB is made as the design config params
        compressed_word_vec = 0
        zero_count = 0
        first_compressed_zero_idx = -1 # to store the index of the first 64 bit number denoting zero count
        for element in self.activation_map:
            if(element == 0):
                zero_count += 1 # count consecutive 0s
            else:
                while(zero_count >= 2**self.count_width - 1):
                    if(count_overflow_tracker + self.count_width < 64): # there is still room inside the 64 bits
                        compressed_zero_vec = compressed_zero_vec | ((2**self.count_width - 1) << count_overflow_tracker)
                        count_overflow_tracker += self.count_width
                        zero_count -= (2**self.count_width - 2)
                    else: # need to move some bits of the current count to the next compressed word
                        compressed_zero_vec = compressed_zero_vec | (((2**self.count_width - 1) << count_overflow_tracker) & 0xFFFFFFFFFFFFFFFF)
                        if(first_compressed_zero_idx == -1):
                            first_compressed_zero_idx = len(self.input_list) # mark the position of first compressed zero count vector
                        self.input_list.append(compressed_zero_vec) # add the compressed zero count vector to the list
                        compressed_zero_vec = (2**self.count_width - 1) >> (64 - count_overflow_tracker) # make the new compressed zero vector with the remaining bits
                        count_overflow_tracker += self.count_width
                        count_overflow_tracker %= 64 # reset the overflow tracker
                        zero_count -= (2**self.count_width - 2)

                if(zero_count > 0):
                    if(count_overflow_tracker + self.count_width < 64): # there is still room inside the 64 bits
                        compressed_zero_vec = compressed_zero_vec | (zero_count << count_overflow_tracker)
                        count_overflow_tracker += self.count_width
                        zero_count = 0 # all 0s upto this point accounted correctly now
                        compressed_word_vec = compressed_word_vec | ((element << word_overflow_tracker) & 0xFFFFFFFFFFFFFFFF) # add the word to the compressed word vec
                        word_overflow_tracker += (self.word_width * 4) # no issues here since all possible word_width values is a factor of 64
                        if(word_overflow_tracker == 64): # compressed word vector full
                            self.input_list.append(compressed_word_vec)
                            if(len(str(bin(compressed_word_vec))[2:]) > 64):
                                print("word overflow")
                            word_overflow_tracker = 0
                            compressed_word_vec = 0
                    else: # need to move some bits of the current count to the next compressed word
                        compressed_zero_vec = compressed_zero_vec | ((zero_count << count_overflow_tracker) & 0xFFFFFFFFFFFFFFFF)
                        if(first_compressed_zero_idx == -1):
                            first_compressed_zero_idx = len(self.input_list)
                        self.input_list.append(compressed_zero_vec)
                        compressed_zero_vec = zero_count >> (64 - count_overflow_tracker)
                        count_overflow_tracker += self.count_width
                        count_overflow_tracker %= 64
                        zero_count = 0
                        compressed_word_vec = compressed_word_vec | ((element << word_overflow_tracker) & 0xFFFFFFFFFFFFFFFF)
                        word_overflow_tracker += (self.word_width * 4)
                        if(word_overflow_tracker == 64):
                            self.input_list.append(compressed_word_vec)
                            word_overflow_tracker = 0
                            compressed_word_vec = 0

        if(count_overflow_tracker != 0): # final compressed zero vector that did not overflow yet
            if(first_compressed_zero_idx == -1):
                first_compressed_zero_idx = len(self.input_list)
            self.input_list.append(compressed_zero_vec)
        if(word_overflow_tracker != 0): # final compressed word vector that did not overflow yet
            self.input_list.append(compressed_word_vec)
        self.input_list.insert(0, self.input_list.pop(first_compressed_zero_idx))

        # Initial compressed input alone will have details of word width and count width
        n2 = 0
        while n2 < len(self.input_list):
            if(self.dut.RDY_ma_get_inputs != 1):
                yield RisingEdge(self.dut.CLK)
            else:
                # print(" Compressed input : ",n1,n2)
                yield self.tb.input_drv.send(InputTransaction(self.tb, 1, self.input_list[n2]))
                yield self.tb.input_drv.send(InputTransaction(self.tb, 0, 0))
                for delay in range(2):
                    yield RisingEdge(self.dut.CLK)
                n2 += 1

        self.rl_done = True

    @cocotb.coroutine
    def terminate_rl_episode(self):
        print("Driven all inputs for this episode ")
        for delay in range(5):
            yield RisingEdge(self.dut.CLK)
        if(self.dut.RDY_ma_send_decompressed_output == 1):
            yield FallingEdge(self.dut.RDY_ma_send_decompressed_output)

        self.coverage_coroutine.kill()
        self.get_output_coroutine.kill()

        for delay in range(10):
            yield RisingEdge(self.dut.CLK)

        self.clock_coroutine.kill()

        # print(tb.expected_output.count)
        # print(tb.expected_output)
        # print(tb.got_output.count)
        # print(tb.got_output)
        self.tb.compare_outputs()
        print('Outputs compared')
        self.tb.start_decompression=1
        self.tb.next_count=0
        self.tb.next_word=0
        self.tb.cont_count=0

        self.tb.decompress_word=0
        self.tb.compressed_word=0
        self.tb.compressed_count=0
        self.tb.zero_counter=64
        self.tb.word_counter=64
        self.tb.counter=0
        self.tb.count_valid=0

    def finish_experiment(self):
        self.tb.stop()
        yield RisingEdge(self.dut.CLK)

@cocotb.coroutine
def monitor_signals(dut, cocotb_coverage, count_width):
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
        cocotb_coverage.append(s)

@cocotb.test()
def run_test(dut):
    cocotb_env = RLEDecompressorCocotbEnv(dut, gym.spaces.Discrete(1))
    yield cocotb_env.run()
    utils.visualize(cocotb_env.log_file_name)
