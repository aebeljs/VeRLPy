import cocotb
from test_rle_compressor_cocotb import *
from collections import Counter
import matplotlib.pyplot as plt
import gym
from multiprocessing import *
import re
import numpy as np
import math
import configparser, ast, logging

def match(patterns, seq):
    if((len(patterns) == 0) or (len(patterns[0]) == 0) or (len(seq) < len(patterns[0]))):
        return 0 # idle state is taken as the first state
    window = len(patterns[0])
    for state in range(len(patterns)):
        x = re.search(patterns[state], seq[-window:])
        if(x is not None):
            return state
    return 0

class RLECompressorSingleStateEnv(gym.Env):
    def __init__(self, num_action_params, coverage_bins, events_rewarded, conn):
        self.num_action_params = num_action_params
        self.coverage_bins = coverage_bins
        self.action_space = gym.spaces.Box(0., 1., (self.num_action_params, ))
        self.observation_space = gym.spaces.Discrete(1) # single state approach so this is enough
        self.total_binary_coverage = [0] * coverage_bins
        self.total_coverage = Counter([])
        self.chosen_actions = []
        self.reward_list = []
        self.events_rewarded = events_rewarded
        self.conn = conn
        for i in range(self.num_action_params):
            self.chosen_actions.append([])

    def step(self, action):
        global episode
        print("Taking RL step")
        observation = 0 # always constant as it is single state
        generator_probab = []
        for i in range(self.num_action_params):
            generator_probab.append(action[i])
            self.chosen_actions[i].append(action[i])
        logging.info('RL | Episode ' + str(episode) + ' | action | ' + str(generator_probab))
        self.conn.send(generator_probab)
        coverage = self.conn.recv()
        logging.info('RL | Episode ' + str(episode) + ' | coverage | ' + str(coverage))
        observation, done, info = 0, True, {}

        binary_coverage = [0] * self.coverage_bins
        for item in coverage:
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])
        logging.info('RL | Episode ' + str(episode) + ' | binary_coverage | ' + str(binary_coverage))

        self.total_coverage.update(Counter(coverage))

        reward = get_reward_based_on_states_visited(binary_coverage, self.events_rewarded)
        logging.info('RL | Episode ' + str(episode) + ' | reward | ' + str(reward))
        logging.info('RL | Episode ' + str(episode) + ' | observation | ' + str(observation))
        logging.info('RL | Episode ' + str(episode) + ' | done | ' + str(done))
        logging.info('RL | Episode ' + str(episode) + ' | info | ' + str(info))
        print('reward:', reward)
        self.reward_list.append(reward)
        return observation, reward, done, info

    def reset(self):
        global episode
        state = 0
        print('reset called')
        # reset device and testbench here too
        logging.info('RL | Episode ' + str(episode) + ' | reset called')
        episode += 1
        return state

def get_reward_based_on_states_visited(binary_coverage, events_rewarded):
    reward = 0
    for item in events_rewarded:
        reward += binary_coverage[item]
    return reward

def rl_run(conn):
    config = configparser.ConfigParser()
    config.read('config.ini')
    COVERAGE_BINS = config['main'].getint('num_events')
    logging.info('CONFIG | num_events | ' + str(COVERAGE_BINS))
    NUM_EPISODES = config['main'].getint('num_episodes')
    logging.info('CONFIG | num_episodes | ' + str(NUM_EPISODES))
    EVENTS_REWARDED = ast.literal_eval(config['main']['events_rewarded'])
    logging.info('CONFIG | events_rewarded | ' + str(EVENTS_REWARDED))
    NUM_SEQ_GEN_PARAMS = len(ast.literal_eval(config['cocotb']['fsm_states']))
    logging.info('CONFIG | fsm_states | ' + str(NUM_SEQ_GEN_PARAMS))
    NUM_DESIGN_ENV_PARAMS = len(ast.literal_eval(config['cocotb']['discrete_params']))
    NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS

    suffix1 = '_reward=1,3,4,history=' + str(int(np.log2(NUM_SEQ_GEN_PARAMS)))
    suffix = "_N=" + 'x100' + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + '4' + ',count_width=' + 'var'

    env = RLECompressorSingleStateEnv(NUM_ACTION_PARAMS, COVERAGE_BINS, EVENTS_REWARDED, conn)

    from stable_baselines3 import DDPG, SAC
    from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

    # The noise objects for DDPG
    n_actions = env.action_space.shape[-1]
    action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))

    # model = DDPG("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=300, learning_rate=0.001, train_freq=(5, 'episode'))
    learning_starts = config['RL'].getint('learning_starts')
    logging.info('CONFIG | learning_starts | ' + str(learning_starts))
    learning_rate = config['RL'].getfloat('learning_rate')
    logging.info('CONFIG | learning_rate | ' + str(learning_rate))
    train_freq = ast.literal_eval(config['RL']['train_freq'])
    logging.info('CONFIG | train_freq | ' + str(train_freq))
    model = SAC("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=learning_starts, learning_rate=learning_rate, train_freq=train_freq)
    suffix1 = '_' + type(model).__name__ + suffix1
    model.learn(total_timesteps=NUM_EPISODES)

    model_save_path = suffix1[1:] + suffix
    model.save(model_save_path)

    print(env.total_binary_coverage)
    plt.vlines(list(range(COVERAGE_BINS)), 0, env.total_binary_coverage, color='C0', lw=4)
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
episode = 0

import logging
# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='test.log',
                            filemode='w',
                            format='%(asctime)s | %(levelname)s | %(message)s',
                            datefmt='%d/%m/%Y %I:%M:%S %p',
                            level=logging.INFO)

@cocotb.coroutine
def monitor_signals(dut):
    global count_width
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_word_counter.value == 16),
            (int)(dut.rg_zero_counter.value == 64),
            (int)(dut.rg_counter.value == (2**count_width - 2)),
            (int)(dut.rg_next_count != 0),
            (int)((dut.rg_zero_counter.value == 64) and (dut.rg_next_count != 0))]
        s = ''.join(map(str, s))
        cocotb_coverage.append(s)

@cocotb.test()
def run_test(dut):
    config = configparser.ConfigParser()
    config.read('config.ini')

    parent_conn, child_conn = Pipe()
    rl_process = Process(target=rl_run, args=(child_conn,))
    rl_process.start()

    NUM_EPISODES = config['main'].getint('num_episodes')

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

    FSM_states = ast.literal_eval(config['cocotb']['fsm_states'])
    discrete_params = ast.literal_eval(config['cocotb']['discrete_params'])
    num_discrete_params = len(discrete_params)
    discrete_param_values = []
    for param in discrete_params:
        discrete_param_values.append(ast.literal_eval(config['discrete'][param]))

    for i in range(NUM_EPISODES):
        print("-----------------------------------------------")
        print("Epsiode number: ", i)

        cocotb_coverage.clear()
        history = ''

        # get action
        print('waiting for RL action', i)
        Z = parent_conn.recv()
        print("action: ", Z)
        Z = [float(i) for i in Z]
        logging.info('cocotb | Episode ' + str(i + 1) + ' | action | ' + str(Z))

        discrete_actions = []
        for j in range(num_discrete_params):
            x = math.ceil(Z[j - num_discrete_params] * len(discrete_param_values[j]))
            if((x == 0) and (len(discrete_param_values[j]) != 0)):
                x = 1
            discrete_actions.append(discrete_param_values[j][x - 1])

        count_width = discrete_actions[0]
        print('count width', count_width)
        tb.count_width = count_width

        N = discrete_actions[1]
        print('N =', N)

        Z = Z[:-num_discrete_params]

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
        logging.info('cocotb | Episode ' + str(i + 1) + ' | history | ' + history)
        parent_conn.send(cocotb_coverage)

    rl_process.join()
    tb.stop()
