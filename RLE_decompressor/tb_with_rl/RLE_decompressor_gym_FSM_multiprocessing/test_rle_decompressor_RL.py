import cocotb
from test_rle_decompression_cocotb import *
from collections import Counter
import matplotlib.pyplot as plt
import gym
from multiprocessing import *
import re
import numpy as np
import math

def match(patterns, seq):
    if((len(patterns) == 0) or (len(patterns[0]) == 0) or (len(seq) < len(patterns[0]))):
        return 0 # idle state is taken as the first state
    window = len(patterns[0])
    for state in range(len(patterns)):
        x = re.search(patterns[state], seq[-window:])
        if(x is not None):
            return state
    return 0

class RLEDecompressorSingleStateEnv(gym.Env):
    def __init__(self, num_action_params, coverage_len, conn):
        self.num_action_params = num_action_params
        self.coverage_len = coverage_len
        self.action_space = gym.spaces.Box(0., 1., (self.num_action_params, ))
        self.observation_space = gym.spaces.Discrete(1) # single state approach so this is enough
        self.total_binary_coverage = [0] * coverage_len
        self.total_coverage = Counter([])
        self.chosen_actions = []
        self.reward_list = []
        self.conn = conn
        for i in range(self.num_action_params):
            self.chosen_actions.append([])

    def step(self, action):
        observation = 0 # always constant as it is single state
        generator_probab = []
        for i in range(self.num_action_params):
            generator_probab.append(action[i])
            self.chosen_actions[i].append(action[i])
        print(generator_probab)
        self.conn.send(generator_probab)
        print('action write done----------------------')
        coverage = self.conn.recv()
        observation, done, info = 0, True, {}

        binary_coverage = [0] * self.coverage_len
        for item in coverage:
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])

        self.total_coverage.update(Counter(coverage))

        reward = get_reward_based_on_states_visited(binary_coverage)
        print('reward:', reward)
        self.reward_list.append(reward)
        return observation, reward, done, info

    def reset(self):
        state = 0
        print('reset called')
        # reset device and testbench here too
        return state

def get_reward_based_on_states_visited(binary_coverage):
    reward = 0
    events_rewarded = [5]
    for item in events_rewarded:
        reward += binary_coverage[item]
    return reward

def rl_run(conn):
    COVERAGE_LEN = 8
    NUM_EPISODES = 10
    conn.send([NUM_EPISODES])
    NUM_SEQ_GEN_PARAMS = int(conn.recv()[0])
    NUM_DESIGN_ENV_PARAMS = 0
    NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS

    suffix1 = '_reward=5_history=' + str(np.log2(NUM_ACTION_PARAMS))
    suffix = "_N=" + '400' + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + '4' + ',count_width=' + '6'

    env = RLEDecompressorSingleStateEnv(NUM_ACTION_PARAMS, COVERAGE_LEN, conn)

    # from stable_baselines3.common.env_checker import check_env
    # check_env(env) # to check if our env is in gym format

    from stable_baselines3 import DDPG
    from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

    # The noise objects for DDPG
    n_actions = env.action_space.shape[-1]
    action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))

    model = DDPG("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=5, learning_rate=0.005, train_freq=(2, 'episode'))
    model.learn(total_timesteps=NUM_EPISODES)

    model.save('DDPG_decompressor_num_action_params=' + str(env.num_action_params))

    print(env.total_binary_coverage)
    plt.vlines(list(range(COVERAGE_LEN)), 0, env.total_binary_coverage, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of individual event coverage\n")
    plt.savefig('./hist_of_binary_coverage' + suffix1 + suffix + '.png', bbox_inches='tight')
    plt.close()

    env.total_coverage = sorted(env.total_coverage.items())
    labels = [x[0] for x in env.total_coverage]
    counts = [x[1] for x in env.total_coverage]
    plt.vlines(labels, 0, counts, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of combination event coverage\n")
    plt.savefig('./hist_of_coverage' + suffix1 + suffix + '.png', bbox_inches='tight')
    plt.close()

    plt.plot(env.reward_list)
    plt.grid()
    plt.tight_layout()
    plt.title("Reward vs episode\n")
    plt.savefig('./reward_plot' + suffix1 + suffix + '.png', bbox_inches='tight')
    plt.close()

    for i in range(NUM_ACTION_PARAMS):
        plt.hist(env.chosen_actions[i], bins=100)
        plt.tight_layout()
        plt.title('Histogram of action param ' + str(i) +  ' in the activation map\n')
        plt.savefig('./hist_of_actions'+ '_param=' + str(i) + suffix1 + suffix + '.png', bbox_inches='tight')
        plt.close()

cocotb_coverage = []
count_width = 6
word_width = 4
random.seed(1)

@coroutine
def monitor_signals(dut):
    global count_width
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
    parent_conn, child_conn = Pipe()
    rl_process = Process(target=rl_run, args=(child_conn,))
    rl_process.start()

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut))
    tb = Testbench(dut)
    cocotb.fork(get_decompressed_output(dut,tb))

    NUM_EPISODES = int(parent_conn.recv()[0])
    print('episodes', NUM_EPISODES)
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
    parent_conn.send([len(FSM_states)])

    # suffix = "_m=" + str(M) + ",numEps=" + str(NUM_EPISODES)
    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + str(word_width) + ',count_width=' + str(count_width)
    for n1 in range(NUM_EPISODES):
        print('------------------------')
        print("Episode : ", n1)
        # word_width = random.choice([1,2,4,8])
        # count_width = random.randint(2,8)

        cocotb_coverage.clear()
        activation_map.clear()
        input_list.clear()
        history = ''

        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        print('waiting for RL action', n1)
        Pr_zero = parent_conn.recv()
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

        # Initial compressed input alone will have details of word width and count width
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
        parent_conn.send(cocotb_coverage)

    tb.stop()
