import cocotb
from test_rle_decompression_cocotb import *
from collections import Counter
import matplotlib.pyplot as plt
import gym
from multiprocessing import *
import re
import numpy as np
import math
from numpy.random import choice

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
    def __init__(self, num_action_params, coverage_len, conn, NUM_EPISODES):

        self.num_action_params = num_action_params
        self.coverage_len = coverage_len
        self.action_space = gym.spaces.Box(0., 1., (self.num_action_params, ))
        #self.action_space = gym.spaces.Discrete(100)
        self.observation_space = gym.spaces.Discrete(1) # single state approach so this is enough
        self.total_binary_coverage = [0] * coverage_len
        self.total_coverage = Counter([])
        self.chosen_actions = []
        self.reward_list = []
        self.conn = conn
        self.eps_counter=0
        self.num_episodes=NUM_EPISODES;
        for i in range(self.num_action_params):
            self.chosen_actions.append([])

    def step(self, action):
        self.eps_counter=self.eps_counter+1
        observation = 0 # always constant as it is single state
        generator_probab = []
        for i in range(self.num_action_params):
            generator_probab.append(action[i])
            self.chosen_actions[i].append(action[i])
            #generator_probab.append(action/100.0)
            #self.chosen_actions[i].append(action/100.0)
        #print(generator_probab)
        self.conn.send(generator_probab)
        
        #print('action write done----------------------')
        
        coverage = self.conn.recv()
        norms=self.conn.recv()
        norm_eps1=norms[0];
        random_norm=norms[1];
        reward_state1=self.conn.recv()
        ab_array=self.conn.recv()

        observation, done, info = 0, True, {}

        binary_coverage = [0] * self.coverage_len
        for item in coverage:
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])

        self.total_coverage.update(Counter(coverage))

        reward = get_reward_based_on_states_visited(binary_coverage,norm_eps1,random_norm,reward_state1,ab_array,self.num_episodes)
        #print('reward:', reward)

        self.reward_list.append(reward)
        if(self.eps_counter==self.num_episodes):
            self.conn.send(self.total_binary_coverage)
        return observation, reward, done, info

    def reset(self):
        state = 0
        #print('reset called')
        # reset device and testbench here too
        return state

def get_reward_based_on_states_visited(binary_coverage,norm_eps1,random_norm,reward_state1,ab_array,no_eps):
    global norm_eps
    num_a=ab_array[0];
    num_b=ab_array[1];
    reward = 0
    reward_state1=int(5)
    events_rewarded = [reward_state1]
    for item in events_rewarded:
        reward += binary_coverage[item]
    #return reward
    return (reward*random_norm/norm_eps1)
    #return ((num_a+(reward*no_eps))/(num_b+(norm_eps*no_eps)))*(num_b/num_a)

def rl_run(conn):
    COVERAGE_LEN = 8
    NUM_EPISODES = 1000
    conn.send([NUM_EPISODES])
    NUM_SEQ_GEN_PARAMS = int(conn.recv()[0])
    NUM_DESIGN_ENV_PARAMS = 0
    NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS

    suffix1 = '_reward=5_history=' + str(np.log2(NUM_ACTION_PARAMS))
    suffix = "_N=" + '400' + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + '4' + ',count_width=' + '6'

    env = RLEDecompressorSingleStateEnv(NUM_ACTION_PARAMS, COVERAGE_LEN, conn, NUM_EPISODES)

    # from stable_baselines3.common.env_checker import check_env
    # check_env(env) # to check if our env is in gym format

    
    from stable_baselines3 import DDPG, SAC, DQN
    from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

    # The noise objects for DDPG
    n_actions = env.action_space.shape[-1]
    #n_actions =100
    action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))
    
    

    #model = DDPG("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=40, learning_rate=0.001, train_freq=(5, 'episode')) ##MODIFY HYPER PARAMS
    #from stable_baselines.deepq.policies import MlpPolicy
    
    #model = DQN("MlpPolicy", env, verbose=1, learning_starts=100, target_update_interval=10)

    #model = SAC("MlpPolicy", env, action_noise=action_noise, verbose=1,learning_starts=100, learning_rate=0.0003,train_freq=(1, 'episode'))
    model = SAC("MlpPolicy", env, action_noise=action_noise, verbose=1,learning_starts=100)

    model.learn(total_timesteps=NUM_EPISODES)

    #model.save('DDPG_decompressor_num_action_params=' + str(env.num_action_params))

    print("env.total_binary_coverage=",env.total_binary_coverage)
    '''
    plt.vlines(list(range(COVERAGE_LEN)), 0, env.total_binary_coverage, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of individual event coverage\n")
    plt.savefig('./hist_of_binary_coverage' + suffix1 + suffix + '.png', bbox_inches='tight')
    plt.close()
    '''
    env.total_coverage = sorted(env.total_coverage.items())
    labels = [x[0] for x in env.total_coverage]
    counts = [x[1] for x in env.total_coverage]
    
    '''
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
    '''

cocotb_coverage = []
norm_factor=0.0;
norm_eps=0.0;
count_width = 6
word_width = 4
random.seed(1)

@coroutine
def monitor_signals(dut):
    global count_width

    global norm_factor
    global norm_eps

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
        norm_eps=norm_eps+1;
        norm_factor=norm_factor+1;
        #print("norm=",norm_eps)


@cocotb.test()
def run_test(dut):

    global word_width
    global count_width
    
    global norm_eps
    global norm_factor

    counter_iter=0;
    MAX_ITER=50;
    reward_state=int(2);
    COVERAGE_LEN=8;
    factor_array=np.array([0.0]*COVERAGE_LEN)
    start_val=0.05
    for i in range(0, len(factor_array)):
        factor_array[i]=start_val;
    accumulated_binary_coverage=np.array([0.0]*COVERAGE_LEN)
    prev_probs=np.array([0.0]*COVERAGE_LEN)
    position_state=int(0);
    chosen_actions=[];
    rn_norm=0.0;
    num_a=start_val;
    num_b=start_val;


    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut))
    
    tb = Testbench(dut)
    cocotb.fork(get_decompressed_output(dut,tb))
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
    
    while(counter_iter<MAX_ITER):
        parent_conn, child_conn = Pipe()
        rl_process = Process(target=rl_run, args=(child_conn,))
        rl_process.start()
        NUM_EPISODES = int(parent_conn.recv()[0])
        print('episodes', NUM_EPISODES)
        parent_conn.send([len(FSM_states)])

        all_labels=range(COVERAGE_LEN);
        all_labels=[str(i) for i in all_labels]

        print("factor_array=",factor_array)
        print("acc_bin_cvrg=",accumulated_binary_coverage)

        if(counter_iter>0):
            probabs=accumulated_binary_coverage/norm_factor
            #probabs=-1*np.exp(-probabs/(1/COVERAGE_LEN))*np.log(probabs)
            probabs=-1*((1-probabs)**3)*np.log(probabs)
            probabs=probabs/np.sum(probabs)
            print("probabs_before=",probabs)
            probabs=probabs*factor_array;
            probabs=probabs/np.sum(probabs)
            print("probabs_after=",probabs)
            #probabs=np.exp(6*probabs);
            #probabs=probabs/np.sum(probabs);
            state_chosen=choice(all_labels,1,p=probabs,replace=False)[0];
            position_state=all_labels.index(state_chosen);
            print("state_rewarded(not position)=",position_state+1)
            num_a=accumulated_binary_coverage[position_state];

            #reward_state=position_state;

            for i in range(0,len(accumulated_binary_coverage)):
                prev_probs[i]=accumulated_binary_coverage[i]/norm_factor;


        # suffix = "_m=" + str(M) + ",numEps=" + str(NUM_EPISODES)
        suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + str(word_width) + ',count_width=' + str(count_width)
        for n1 in range(NUM_EPISODES):
            print('------------------------')
            print("Episode : ", n1)

            # word_width = random.choice([1,2,4,8])
            # count_width = random.randint(2,8)
            norm_eps=0;

            cocotb_coverage.clear()
            activation_map.clear()
            input_list.clear()
            history = ''

            dut.RST_N <= 0
            yield Timer(2)
            dut.RST_N <= 1

            for delay in range(10):
                yield RisingEdge(dut.CLK)

            #print('waiting for RL action', n1)
            Pr_zero = parent_conn.recv()
            if(counter_iter==0):
                Pr_zero=[0]*len(Pr_zero)
                for i in range(0,len(Pr_zero)):
                    Pr_zero[i]=(int)(random.random() * 100) / 100.
            
            print('Probab:', Pr_zero)    
            Pr_zero = [float(i) for i in Pr_zero]
            file3 = open("results_decomp_sac1000_chosen_actions", "a")
            file3.write(str(Pr_zero [0]))
            file3.write("\n");

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

            #print("Driven all inputs for this episode ")
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
            #print('Outputs compared')
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
            
            
            if(counter_iter==0):
                parent_conn.send([norm_eps,0])
            else:
                parent_conn.send([norm_eps,rn_norm])            
            print("norm_eps=",norm_eps)
            parent_conn.send(position_state)
            parent_conn.send([num_a,num_b])

            if(counter_iter==0):
                rn_norm=((rn_norm*n1)+norm_eps)/(n1+1);

            
            if(n1==(NUM_EPISODES-1)):    
                run_binary_coverage=parent_conn.recv()
                #print("1)",run_binary_coverage)
                run_binary_coverage=np.array(run_binary_coverage)
                #print("2)",run_binary_coverage)
                accumulated_binary_coverage=accumulated_binary_coverage+run_binary_coverage;
                #print("3)acc=",accumulated_binary_coverage)
                curr_probs=accumulated_binary_coverage/norm_factor;
                num_b=norm_factor

                if(counter_iter>0):
                    f1=((curr_probs[position_state]-prev_probs[position_state])/prev_probs[position_state]);
                    f1=10*f1-np.log(99);
                    f1=1/(1+np.exp(-1*f1));
                    factor_array[position_state]=f1;
                    print(curr_probs[position_state],prev_probs[position_state],",arg=",f1,",position_state=",position_state)

                file1 = open("results_decomp_sac1000_all", "a")
                file2 = open("results_decomp_sac1000_probs", "a")
                ww=str(list(curr_probs))
                ww=ww[1:len(ww)-1]
                file2.write(ww)
                file2.write("\n");
                file2.close();
                
                file1.write("reward_state=")
                w1=str(position_state);
                file1.write(w1);
                file1.write("\n");
                file1.write("current_hist=")
                w1=str(run_binary_coverage);
                file1.write(w1);
                file1.write("\n");
                w2=str(list(accumulated_binary_coverage));
                file1.write(w2);
                file1.write("\n");
                file1.write("den=")
                w3=str(counter_iter+1);
                file1.write(w3);
                file1.write("\n");
                file1.write("curr_probs=")
                file1.write(str(list(curr_probs)))
                file1.write("\n");
                file1.write("norm_factor=")
                w3=str(norm_factor);
                file1.write(w3);
                file1.write("\n");
                file1.write("\n \n");
                file1.close();

        rl_process.join()
        counter_iter=counter_iter+1;
        print("norm_factor=",norm_factor)

    tb.stop()
