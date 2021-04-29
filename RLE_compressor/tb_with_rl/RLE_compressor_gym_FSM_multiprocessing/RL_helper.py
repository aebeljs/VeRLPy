from collections import Counter
import gym
import re
import configparser, ast, math
import numpy as np

episode = 0
def match(patterns, seq):
    if((len(patterns) == 0) or (len(patterns[0]) == 0) or (len(seq) < len(patterns[0]))):
        return 0 # idle state is taken as the first state
    window = len(patterns[0])
    for state in range(len(patterns)):
        x = re.search(patterns[state], seq[-window:])
        if(x is not None):
            return state
    return 0

class SingleStateHWVerifEnv(gym.Env):
    def __init__(self, num_action_params, coverage_bins, events_rewarded, conn, logger):
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
        self.logger = logger
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
        self.logger.info('RL | Episode ' + str(episode) + ' | action | ' + str(generator_probab))
        self.conn.send(generator_probab)
        coverage = self.conn.recv()
        self.logger.info('RL | Episode ' + str(episode) + ' | coverage | ' + str(coverage))
        observation, done, info = 0, True, {}

        binary_coverage = [0] * self.coverage_bins
        for item in coverage:
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])
        self.logger.info('RL | Episode ' + str(episode) + ' | binary_coverage | ' + str(binary_coverage))

        self.total_coverage.update(Counter(coverage))

        reward = get_reward_based_on_states_visited(binary_coverage, self.events_rewarded)
        self.logger.info('RL | Episode ' + str(episode) + ' | reward | ' + str(reward))
        self.logger.info('RL | Episode ' + str(episode) + ' | observation | ' + str(observation))
        self.logger.info('RL | Episode ' + str(episode) + ' | done | ' + str(done))
        self.logger.info('RL | Episode ' + str(episode) + ' | info | ' + str(info))
        print('reward:', reward)
        self.reward_list.append(reward)
        return observation, reward, done, info

    def reset(self):
        global episode
        state = 0
        print('reset called')
        # reset device and testbench here too
        self.logger.info('RL | Episode ' + str(episode) + ' | reset called')
        episode += 1
        return state

def get_reward_based_on_states_visited(binary_coverage, events_rewarded):
    reward = 0
    for item in events_rewarded:
        reward += binary_coverage[item]
    return reward

def rl_run(conn, logger, timestamp):
    config = configparser.ConfigParser()
    config.read('config.ini')
    COVERAGE_BINS = config['main'].getint('num_events')
    logger.info('CONFIG | num_events | ' + str(COVERAGE_BINS))
    NUM_EPISODES = config['main'].getint('num_episodes')
    logger.info('CONFIG | num_episodes | ' + str(NUM_EPISODES))
    EVENTS_REWARDED = ast.literal_eval(config['main']['events_rewarded'])
    logger.info('CONFIG | events_rewarded | ' + str(EVENTS_REWARDED))
    NUM_SEQ_GEN_PARAMS = len(ast.literal_eval(config['cocotb']['fsm_states']))
    logger.info('CONFIG | fsm_states | ' + str(NUM_SEQ_GEN_PARAMS))
    NUM_DESIGN_ENV_PARAMS = len(ast.literal_eval(config['cocotb']['discrete_params']))
    NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS

    # suffix1 = '_reward=1,3,4,history=' + str(int(np.log2(NUM_SEQ_GEN_PARAMS)))
    # suffix = "_N=" + 'x100' + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + '4' + ',count_width=' + 'var'

    env = SingleStateHWVerifEnv(NUM_ACTION_PARAMS, COVERAGE_BINS, EVENTS_REWARDED, conn, logger)

    from stable_baselines3 import DDPG, SAC
    from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

    # The noise objects for DDPG
    n_actions = env.action_space.shape[-1]
    action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))

    # model = DDPG("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=300, learning_rate=0.001, train_freq=(5, 'episode'))
    learning_starts = config['RL'].getint('learning_starts')
    logger.info('CONFIG | learning_starts | ' + str(learning_starts))
    learning_rate = config['RL'].getfloat('learning_rate')
    logger.info('CONFIG | learning_rate | ' + str(learning_rate))
    train_freq = ast.literal_eval(config['RL']['train_freq'])
    logger.info('CONFIG | train_freq | ' + str(train_freq))
    model = SAC("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=learning_starts, learning_rate=learning_rate, train_freq=train_freq)
    model.learn(total_timesteps=NUM_EPISODES)
    model.save('model_' + timestamp)

    logger.info('RL | result | total_binary_coverage | ' + str(env.total_binary_coverage))

    print(env.total_binary_coverage)

    env.total_coverage = sorted(env.total_coverage.items())
    labels = [x[0] for x in env.total_coverage]
    counts = [x[1] for x in env.total_coverage]
    logger.info('RL | result | total_coverage | ' + str(labels) + ' | ' + str(counts))

    logger.info('RL | result | reward_plot | ' + str(env.reward_list))

    for i in range(NUM_ACTION_PARAMS):
        logger.info('RL | result | action_hist_' + str(i + 1) + ' | ' + str(env.chosen_actions[i]))
