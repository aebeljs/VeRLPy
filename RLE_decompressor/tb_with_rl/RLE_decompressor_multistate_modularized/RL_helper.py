from collections import Counter
import gym
import re
import configparser
import ast
import math
import numpy as np

step_count = 0     # to track the episode count


def get_next_state_of_FSM(binary_seq, patterns):
    '''
    Function for FSM based binary sequence generation

    Inputs
    binary_seq: A string containing the binary sequence against which the regex
                patterns are compared to determine the state transition of the FSM
                and the corresponding probability knob to be used when in the new
                state
                eg: '011010110001', '1101', etc.

    patterns  : A list of regex patterns corresponding to each probability knob
                for generating the next element of the sequence. All the elements
                of the list must be strings of the same length and they should
                exhaustively cover the space of possible binary strings of that
                length
                eg: ['00', '01', '1.'], ['0..', '1..'], etc.

    Output
    Returns an integer corresponding to the index of the new state of the FSM.
    Valid values range from 0 to len(patterns)
    eg: 0 corresponds to the state corresponding to the first element of
        patterns
    '''
    if((len(patterns) == 0) or (len(patterns[0]) == 0)
            or (len(binary_seq) < len(patterns[0]))):
        return 0    # idle state of FSM is taken as the first state
    window = len(patterns[0])
    for state in range(len(patterns)):
        x = re.search(patterns[state], binary_seq[-window:])
        if(x is not None):
            return state    # return the matched state index
    return 0


class SingleStateHardwareVerifEnv(gym.Env):
    '''
    OpenAI Gym environment for hardware verification using RL. The Markov state
    space consists of a single state and the inputs to the DUT are parameterized
    and generated using a continuous RL action space as represented by the Box()
    below.
    '''
    def __init__(self, num_action_params, num_events, reward_function,
                 conn, logger):
        # essential for the gym env
        self.action_space = gym.spaces.Box(0., 1., (num_action_params, ))
        self.observation_space = gym.spaces.Discrete(1)  # single Markov state

        self.num_action_params = num_action_params
        self.num_events = num_events
        self.total_binary_coverage = [0] * num_events   # stores the individual event coverage
        self.total_coverage = Counter([])   # stores the combination event coverage
        self.reward_list = []   # stores the rewards given at each episode
        self.reward_function = reward_function  # reward function to be used
        self.conn = conn    # Pipe object connection for communicating with the cocotb process
        self.logger = logger
        self.chosen_actions = []    # stores the actions chosen by the agent over the step_counts
        for i in range(num_action_params):
            self.chosen_actions.append([])

    def step(self, action):
        # essential for the gym env
        self.conn.send('rl_step')
        global step_count
        print('Taking RL step ' + str(step_count))
        generator_probab = []
        for i in range(self.num_action_params):
            generator_probab.append(action[i])
            self.chosen_actions[i].append(action[i])

        self.conn.send(generator_probab)    # send the action to the cocotb process
        coverage = self.conn.recv()     # receive the coverage from the cocotb process

        # calculate this episode's individual event coverage and track total coverage
        binary_coverage = [0] * self.num_events
        for item in coverage:
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])

        reward = self.get_reward_based_on_states_visited(binary_coverage, self.reward_function)
        observation = self.conn.recv()
        done = self.conn.recv()
        info = self.conn.recv()
        #observation, done, info = 0, True, {}   # observation is 0 alwyas for single Markov state space

        print('reward:', reward)
        self.reward_list.append(reward)
        self.total_coverage.update(Counter(coverage))   # update total combination coverage

        self.logger.info('RL | Step ' + str(step_count) + ' | action | ' + str(generator_probab))
        self.logger.info('RL | Step ' + str(step_count) + ' | coverage | ' + str(coverage))
        self.logger.info('RL | Step ' + str(step_count) + ' | binary_coverage | ' + str(binary_coverage))
        self.logger.info('RL | Step ' + str(step_count) + ' | reward | ' + str(reward))
        self.logger.info('RL | Step ' + str(step_count) + ' | observation | ' + str(observation))
        self.logger.info('RL | Step ' + str(step_count) + ' | done | ' + str(done))
        self.logger.info('RL | Step ' + str(step_count) + ' | info | ' + str(info))

        return observation, reward, done, info

    def reset(self):
        # essential for the gym env
        self.conn.send('rl_reset')
        global step_count
        self.logger.info('RL | Step ' + str(step_count) + ' |dut reset asserted')
        state = 0   # state is constant as it is a single Markov state space
        # DUT reset should get called during before next step too
        self.logger.info('RL | Step ' + str(step_count) + ' | reset called')
        step_count += 1
        return state

    def get_reward_based_on_states_visited(self, binary_coverage, reward_function):
        '''
        Helper function to calculate the reward to be given in an episode, based
        on the coverage

        Inputs
        binary_coverage: A list of length num_events containing how many times
                         each of the events were hit in an episode of
                         verification
                         eg: if num_events=3, [23, 10, 0]

        reward_function: A list of length num_events containing the multiplier
                         of reward to be given for each event
                         eg: if num_evens=3, [0, 1, 3]

        Output
        Returns the calculated reward. If the inputs are as shown in the examples
        above, the calculated reward will be 23*0 + 10*1 + 0*3 = 10
        '''
        assert (len(binary_coverage) == len(reward_function))
        reward = 0
        for i in range(len(binary_coverage)):
            reward += (binary_coverage[i] * reward_function[i])
        return reward


def RL_run(conn, logger, timestamp):
    '''
    Entry point of the RL process.

    Inputs
    logger   : The common logger object used across the program. Use the same
               object for logging from the cocotb process.
    timestamp: The timestamp used to identify the saved RL model and log file
    '''
    config = configparser.ConfigParser()
    config.read('config.ini')

    # load parameters from the config file
    NUM_EVENTS = config['main'].getint('num_events')
    NUM_STEPS = config['main'].getint('num_steps')
    REWARD_FUNCTION = ast.literal_eval(config['main']['reward_function'])
    NUM_SEQ_GEN_PARAMS = len(ast.literal_eval(config['cocotb']['fsm_states']))
    NUM_DESIGN_ENV_PARAMS = len(ast.literal_eval(config['cocotb']['discrete_params']))
    NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS

    # initialize the gym environment
    env = SingleStateHardwareVerifEnv(NUM_ACTION_PARAMS, NUM_EVENTS, REWARD_FUNCTION, conn, logger)

    # optional: check structural correctness of the gym env
    # from stable_baselines3.common.env_checker import check_env
    # check_env(env)

    from stable_baselines3 import DDPG, SAC
    from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

    # The noise objects for the actor critic algorithm
    n_actions = env.action_space.shape[-1]
    action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))

    # load hyperparameters for the RL agent from the config file
    learning_starts = config['RL'].getint('learning_starts')
    learning_rate = config['RL'].getfloat('learning_rate')
    train_freq = ast.literal_eval(config['RL']['train_freq'])

    # Run the berification experiment while the RL agent learns
    model = SAC("MlpPolicy", env, action_noise=action_noise, verbose=1,
                learning_starts=learning_starts, learning_rate=learning_rate,
                train_freq=train_freq)
    model.learn(total_timesteps=NUM_STEPS)
    model.save('model_' + timestamp)

    print(env.total_binary_coverage)

    # compute the total coverage plot data values to save to the log file
    env.total_coverage = sorted(env.total_coverage.items())
    labels = [x[0] for x in env.total_coverage]
    counts = [x[1] for x in env.total_coverage]

    # log the parameters read from the config file
    logger.info('CONFIG | num_events | ' + str(NUM_EVENTS))
    logger.info('CONFIG | num_steps | ' + str(NUM_STEPS))
    logger.info('CONFIG | reward_function | ' + str(REWARD_FUNCTION))
    logger.info('CONFIG | fsm_states | ' + str(NUM_SEQ_GEN_PARAMS))
    logger.info('CONFIG | learning_starts | ' + str(learning_starts))
    logger.info('CONFIG | learning_rate | ' + str(learning_rate))
    logger.info('CONFIG | train_freq | ' + str(train_freq))

    # log the plot results computed
    logger.info('RL | result | total_binary_coverage | ' + str(env.total_binary_coverage))
    logger.info('RL | result | total_coverage | ' + str(labels) + ' | ' + str(counts))
    logger.info('RL | result | reward_plot | ' + str(env.reward_list))
    for i in range(NUM_ACTION_PARAMS):
        logger.info('RL | result | action_hist_' + str(i + 1) + ' | ' + str(env.chosen_actions[i]))
