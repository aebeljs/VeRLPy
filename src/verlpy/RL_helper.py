from collections import Counter
import gym
import configparser
import ast
import numpy as np
import stable_baselines3
from stable_baselines3.common.noise import NormalActionNoise

step_count = 0     # to track the episode count

class HardwareVerifEnv(gym.Env):
    '''
    OpenAI Gym environment for hardware verification using RL. The Markov state
    space consists of a single state by default and the inputs to the DUT are parameterized
    and generated using a continuous RL action space as represented by the Box()
    below.
    '''
    def __init__(self, num_events, reward_function,
                 conn, logger, observation_space, action_space):
        # essential for the gym env
        self.action_space = action_space
        self.observation_space = observation_space
        self.num_action_params = action_space.shape[-1]

        config = configparser.ConfigParser()
        config.read('config.ini')
        self.log_step = config['main'].getint('log_step')
        self.num_events = num_events
        self.total_binary_coverage = [0] * num_events   # stores the individual event coverage
        self.total_coverage = Counter([])   # stores the combination event coverage
        self.reward_list = []   # stores the rewards given at each episode
        self.reward_function = reward_function  # reward function to be used
        self.conn = conn    # Pipe object connection for communicating with the cocotb process
        self.logger = logger
        self.chosen_actions = []    # stores the actions chosen by the agent over the step_counts
        for i in range(self.num_action_params):
            self.chosen_actions.append([])

    def step(self, action):
        # essential for the gym env
        self.conn.send('RL_step')
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

        print('reward:', reward)
        self.reward_list.append(reward)
        self.total_coverage.update(Counter(coverage))   # update total combination coverage

        if(self.log_step != 0):
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
        self.conn.send('RL_reset')
        global step_count
        state = 0   # assuming that in each episode, the DUT is reset
        if(self.log_step != 0):
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

def tryeval(val):
    '''
    Helper function for converting the string in val to the appropriate type
    '''
    try:
        val = ast.literal_eval(val)
    except ValueError:
        pass
    return val

def RL_run(conn, logger, timestamp, observation_space):
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
    LOWER_BOUNDS = ast.literal_eval(config['continuous']['lower_bounds'])
    UPPER_BOUNDS = ast.literal_eval(config['continuous']['upper_bounds'])
    assert(len(LOWER_BOUNDS) == len(UPPER_BOUNDS))
    NUM_SEQ_GEN_PARAMS = len(LOWER_BOUNDS)
    NUM_DESIGN_ENV_PARAMS = len(ast.literal_eval(config['main']['discrete_params']))
    NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS
    MODE = config['main'].getint('mode')

    # set up action space
    LOWER_BOUNDS.extend([0] * NUM_DESIGN_ENV_PARAMS)
    UPPER_BOUNDS.extend([1] * NUM_DESIGN_ENV_PARAMS)
    action_space = gym.spaces.Box(np.array(LOWER_BOUNDS), np.array(UPPER_BOUNDS), dtype=np.float32)

    # initialize the gym environment
    env = HardwareVerifEnv(NUM_EVENTS, REWARD_FUNCTION, conn, logger, observation_space, action_space)

    # optional: check structural correctness of the gym env
    # from stable_baselines3.common.env_checker import check_env
    # check_env(env)

    # The noise objects for the actor critic algorithm
    n_actions = env.action_space.shape[-1]
    action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))

    # load hyperparameters for the RL agent from the config file
    RL_agent_params = dict(config.items('RL'))
    for k, v in RL_agent_params.items():
        RL_agent_params[k] = tryeval(v)

    if(MODE != 0):
        # Run the verification experiment while the RL agent learns
        RL_algo = getattr(stable_baselines3, config['main']['algorithm'])
        model = RL_algo(env=env, action_noise=action_noise, **RL_agent_params)
        model.learn(total_timesteps=NUM_STEPS)
        model.save('model_' + timestamp)
    else:
        # Generate the random baseline without the RL agent
        env.reset()
        for i in range(NUM_STEPS):
            action = env.action_space.sample()
            obs, rew, done, info = env.step(action)
            if(done):
                env.reset()

    print(env.total_binary_coverage)

    # compute the total coverage plot data values to save to the log file
    env.total_coverage = sorted(env.total_coverage.items())
    labels = [x[0] for x in env.total_coverage]
    counts = [x[1] for x in env.total_coverage]

    # log the parameters read from the config file
    logger.info('CONFIG | num_events | ' + str(NUM_EVENTS))
    logger.info('CONFIG | num_steps | ' + str(NUM_STEPS))
    logger.info('CONFIG | reward_function | ' + str(REWARD_FUNCTION))

    # log the plot results computed
    logger.info('RL | result | total_binary_coverage | ' + str(env.total_binary_coverage))
    logger.info('RL | result | total_coverage | ' + str(labels) + ' | ' + str(counts))
    logger.info('RL | result | reward_plot | ' + str(env.reward_list))
    for i in range(NUM_ACTION_PARAMS):
        logger.info('RL | result | action_hist_' + str(i + 1) + ' | ' + str(env.chosen_actions[i]))
