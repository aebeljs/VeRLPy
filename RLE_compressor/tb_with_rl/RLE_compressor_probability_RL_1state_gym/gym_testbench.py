import gym
import fcntl
import os
import matplotlib.pyplot as plt

class RLECompressorSingleStateEnv(gym.Env):
    def __init__(self):
        self.action_space = gym.spaces.Discrete(100) # 100 possible probability values in {0,1,...99}
        self.observation_space = gym.spaces.Discrete(1) # single state approach so this is enough
        self.total_binary_coverage = [0] * 4
        self.chosen_actions = []

    def step(self, action):
        print("step")
        observation = 0 # always constant as it is single state
        generator_probab = action * 0.01 # converts action to probab value
        print(generator_probab)
        self.chosen_actions.append(generator_probab)
        write_to_file('./RL_output.txt', str(generator_probab))
        print('action write done----------------------')
        coverage = wait_till_read('./cocotb_output.txt')
        observation, done, info = 0, True, {}

        binary_coverage = [0] * 4
        for item in coverage:
            # print(item)
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])
        reward = get_reward_based_on_states_visited(binary_coverage)
        return observation, reward, done, info

    def reset(self):
        state = 0
        print('reset called')
        # reset device and testbench here too
        return state

suffix1 = '_5'
suffix = "_N=" + '400' + ",numEps=" + '1000' + ',word_width=' + '4' + ',count_width=' + '6'
def get_reward_based_on_states_visited(binary_coverage):
    reward = 0
    events_rewarded = [2]
    for item in events_rewarded:
        reward += binary_coverage[item]
    return reward

def write_to_file(filename, content):
    with open(filename, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX) # lock to avoid concurrency issues
        f.write(content)
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

def wait_till_read(filename):
    while(True):
        if(os.path.isfile(filename)):
            with open(filename, "r+") as f:
                fcntl.flock(f, fcntl.LOCK_EX) # lock to avoid concurrency issues
                coverage = [line.rstrip() for line in f]

                if(len(coverage) != 0):
                    # RL has output something
                    f.truncate(0)
                    fcntl.flock(f, fcntl.LOCK_UN)
                    f.close()
                    print(coverage[0])
                    print('length of coverage', len(coverage))
                    break
                fcntl.flock(f, fcntl.LOCK_UN)
                f.close()
    return coverage

from stable_baselines.common.env_checker import check_env
env = RLECompressorSingleStateEnv()

# check_env(env) # to check if our env is in gym format

from stable_baselines.deepq.policies import MlpPolicy
from stable_baselines import DQN

model = DQN(MlpPolicy, env, verbose=1, learning_starts=50, exploration_fraction=0.6, target_network_update_freq=10)
model.learn(total_timesteps=1000)

model.save('DQN_compressor')


print(env.total_binary_coverage)
plt.vlines(list(range(4)), 0, env.total_binary_coverage, color='C0', lw=4)
plt.grid()
plt.xticks(rotation = 90)
plt.tight_layout()
plt.title("Histogram of binary coverage\n")
plt.savefig('./hist_of_binary_coverage' +suffix1+ suffix + '.png', bbox_inches='tight')
plt.close()

plt.hist(env.chosen_actions)
plt.tight_layout()
plt.title("Stochastic input using RL- Histogram of Pr(0) in the activation map\n" + "Reward scheme:"+ suffix1)
plt.savefig('./hist_of_actions'+suffix1 + suffix + '.png', bbox_inches='tight')
plt.close()

# run with this learnt policy
# obs = env.reset()
# for i in range(10):
#     action, _states = model.predict(obs)
#     print(action)
#     # obs, rewards, dones, info = env.step(action)
