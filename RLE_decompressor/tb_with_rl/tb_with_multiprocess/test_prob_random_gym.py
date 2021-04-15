import cocotb
from test_rle_decompression_cocotb import *
import itertools
import matplotlib.pyplot as plt
import sys
from collections import defaultdict
import gym
from multiprocessing import *
import time

coverage = []
total_binary_coverage = [0] * 8
total_set_coverage = []
total_coverage = []
count_width = 6
word_width = 4
random.seed(1)

NUM_EPISODES = 5
N = 400
M = 5

info = {}

drive_input = Value('i',0)
rl_train_done = Value('i',0)
Pr_zero = Value('d',0.5)

observation = Value('i',0)
reward = Value('i',10)
done = Value('i',0)


@cocotb.coroutine
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

def generate_input_list(Pr_zero):
    activation_map = []
    input_list = []
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
    return input_list


class RLEDecompressorSingleStateEnv(gym.Env):
    def __init__(self):
        self.action_space = gym.spaces.Discrete(100) # 100 possible probability values in {0,1,...99}
        self.observation_space = gym.spaces.Discrete(1) # single state approach so this is enough

    def step(self, action):
        print("Starting RL step")
        observation.value = 0 # always constant as it is single state
        generator_probab = action * 0.01 # converts action to probab value
        Pr_zero.value = generator_probab
        drive_input.value = 1
        while(drive_input.value == 1):
            pass
        print("Done RL step")
        lv_done = False
        if(done.value == 1):
            lv_done = True
        return observation.value, reward.value, lv_done, info

    def reset(self):
        state = 0
        return state

def rl_run():
    print("started RL process")
    from stable_baselines.common.env_checker import check_env
    env = RLEDecompressorSingleStateEnv()

    check_env(env) # to check if our env is in gym format

    from stable_baselines.common.policies import MlpPolicy
    from stable_baselines import PPO2

    model = PPO2(MlpPolicy, env, verbose=1)
    model.learn(total_timesteps=5)

    obs = env.reset()

    rl_train_done.value = 1
    print(" Done RL process ")


@cocotb.test()
def run_test(dut):
    tb = Testbench(dut)
    print(dut)
    print(tb)
    cocotb.fork(clock_gen(tb.dut.CLK))
    cocotb.fork(monitor_signals(tb.dut))
    cocotb.fork(get_decompressed_output(dut,tb))

    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + str(word_width) + ',count_width=' + str(count_width)

    rl_process = Process(target=rl_run)
    rl_process.start()

    while rl_train_done.value == 0:
        for delay in range(10):
            yield RisingEdge(tb.dut.CLK)
        if(drive_input.value == 1):
            print("Starting cocotb input driving")
            input_list = generate_input_list(Pr_zero.value)
            #print("Entering tb")
            yield tb.dut_input_drive(input_list)
            #print("Left tb")
            global coverage
            global total_coverage
            total_coverage.extend(coverage)
            global set_coverage
            set_coverage = list(set(coverage))
            print('set coverage:', set_coverage)
            global total_set_coverage
            total_set_coverage.extend(set_coverage)
            for item in coverage:
                for k in range(len(item)):
                    total_binary_coverage[k] += (int)(item[k])
            coverage.clear()
            done.value = 1
            #global info
            #info = {}
            observation.value = 0
            reward.value = 10
            drive_input.value = 0
            print("Done cocotb input driving")
        else:
            yield RisingEdge(tb.dut.CLK)

    rl_process.join()

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