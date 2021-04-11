import gym
import numpy as np
from collections import Counter
from helper import *
import matplotlib.pyplot as plt

c = 0

class RLECompressorSingleStateEnv(gym.Env):
    def __init__(self, num_action_params, coverage_len):
        self.num_action_params = num_action_params
        self.action_space = gym.spaces.Box(0., 1., (self.num_action_params, ))
        self.observation_space = gym.spaces.Discrete(1) # single state approach so this is enough
        self.total_binary_coverage = [0] * coverage_len
        self.total_coverage = Counter([])
        self.chosen_actions = []
        self.reward_list = []
        for i in range(self.num_action_params):
            self.chosen_actions.append([])

    def step(self, action):
        global c
        print('step', c)
        observation = 0 # always constant as it is single state
        generator_probab = []
        for i in range(self.num_action_params):
            generator_probab.append(action[i])
            self.chosen_actions[i].append(action[i])
        print(generator_probab)
        write_to_file('./RL_output.txt', generator_probab)
        print('action write done----------------------')
        coverage = wait_till_read('./cocotb_output.txt')
        observation, done, info = 0, True, {}

        binary_coverage = [0] * COVERAGE_LEN
        for item in coverage:
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])

        self.total_coverage.update(Counter(coverage))

        reward = get_reward_based_on_states_visited(binary_coverage)
        print('reward:', reward)
        self.reward_list.append(reward)
        c += 1
        return observation, reward, done, info

    def reset(self):
        state = 0
        print('reset called')
        # reset device and testbench here too
        return state

def get_reward_based_on_states_visited(binary_coverage):
    reward = 0
    events_rewarded = [4]
    for item in events_rewarded:
        reward += binary_coverage[item]
    return reward

# from stable_baselines.common.env_checker import check_env
# check_env(env) # to check if our env is in gym format

COVERAGE_LEN = 5
NUM_EPISODES = 1000
write_to_file('./RL_output.txt', [NUM_EPISODES])
NUM_SEQ_GEN_PARAMS = int(wait_till_read('./cocotb_output.txt')[0])
NUM_DESIGN_ENV_PARAMS = 2
NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS

# suffix1 = '_reward=2,4_history=' + str(np.log2(NUM_ACTION_PARAMS))
suffix1 = '_reward=4,history=' + str(np.round(np.log2(NUM_SEQ_GEN_PARAMS)))
suffix = "_N=" + 'var' + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + '4' + ',count_width=' + 'var'

env = RLECompressorSingleStateEnv(NUM_ACTION_PARAMS, COVERAGE_LEN)

from stable_baselines3 import DDPG
from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

# The noise objects for DDPG
n_actions = env.action_space.shape[-1]
action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))

model = DDPG("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=995, learning_rate=0.001, train_freq=(5, 'episode'))
model.learn(total_timesteps=NUM_EPISODES)

model.save('DDPG_compressor_num_action_params=' + str(env.num_action_params))

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
