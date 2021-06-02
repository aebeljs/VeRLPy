import cocotb
from test_rle_compressor_cocotb import *
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

class RLECompressorSingleStateEnv(gym.Env):
    def __init__(self, num_action_params, coverage_len, conn, NUM_EPISODES):
        self.num_action_params = num_action_params
        self.coverage_len = coverage_len
        self.action_space = gym.spaces.Box(0., 1., (self.num_action_params, ))
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
        #print("Taking RL step")
        self.eps_counter=self.eps_counter+1
        observation = 0 # always constant as it is single state
        generator_probab = []
        for i in range(self.num_action_params):
            generator_probab.append(action[i])
            self.chosen_actions[i].append(action[i])
        # print(generator_probab)
        self.conn.send(generator_probab)
        # print('action write done----------------------')
        coverage = self.conn.recv()
        norms=self.conn.recv()
        norm_eps1=norms[0];
        random_norm=norms[1];
        reward_state1=self.conn.recv()
        # print('gym', len(coverage))
        observation, done, info = 0, True, {}

        binary_coverage = [0] * self.coverage_len
        for item in coverage:
            for k in range(len(item)):
                binary_coverage[k] += int(item[k])
                self.total_binary_coverage[k] += int(item[k])

        self.total_coverage.update(Counter(coverage))

        reward = get_reward_based_on_states_visited(binary_coverage,norm_eps1,random_norm,reward_state1)
        #print('reward:', reward)
        self.reward_list.append(reward)
        if(self.eps_counter==self.num_episodes):
            print("self.total_binary_coverage=",self.total_binary_coverage)
            self.conn.send(self.total_binary_coverage)

        return observation, reward, done, info

    def reset(self):
        state = 0
        print('reset called')
        # reset device and testbench here too
        return state

def get_reward_based_on_states_visited(binary_coverage,norm_eps1,random_norm,reward_state1):
    reward = 0
    events_rewarded = [reward_state1]
    for item in events_rewarded:
        reward += binary_coverage[item]
    return (reward*random_norm/norm_eps1)

def rl_run(conn):
    # print("started RL process")

    COVERAGE_LEN = 5
    NUM_EPISODES = 50
    conn.send(COVERAGE_LEN)
    conn.send([str(NUM_EPISODES)])
    NUM_SEQ_GEN_PARAMS = int(conn.recv()[0])
    NUM_DESIGN_ENV_PARAMS = 0
    NUM_ACTION_PARAMS = NUM_SEQ_GEN_PARAMS + NUM_DESIGN_ENV_PARAMS

    # suffix1 = '_reward=2,4_history=' + str(np.log2(NUM_ACTION_PARAMS))
    suffix1 = '_reward=1,3,4,history=' + str(np.round(np.log2(NUM_SEQ_GEN_PARAMS)))
    suffix = "_N=" + 'x100' + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + '4' + ',count_width=' + 'var'

    env = RLECompressorSingleStateEnv(NUM_ACTION_PARAMS, COVERAGE_LEN, conn, NUM_EPISODES)

    from stable_baselines3 import DDPG, SAC
    from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise

    # The noise objects for DDPG
    n_actions = env.action_space.shape[-1]
    action_noise = NormalActionNoise(mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions))

    #model = DDPG("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=40, learning_rate=0.001, train_freq=(5, 'episode'))
    #model = SAC("MlpPolicy", env, action_noise=action_noise, verbose=1, learning_starts=40)
    global c_iter
    
    learning_rate_array=[0.0001,0.0003,0.0005,0.0007,0.001]
    train_freq_rate=[1,3,5]

    model = SAC("MlpPolicy", env, action_noise=action_noise, verbose=1,learning_starts=100, learning_rate=learning_rate_array[int(c_iter/3)],train_freq=(train_freq_rate[int(c_iter/15)], 'episode'))
    model.learn(total_timesteps=NUM_EPISODES)
    file1 = open("results_state2_comp_sac250_tuning_all", "a")
    ww="learning rate="+str(learning_rate_array[int(c_iter/3)])+", train freq="+ str(train_freq_rate[int(c_iter/15)])
    file1.write(ww)
    file1.write(", c_iter="+str(c_iter))
    file1.write("\n");
    file1.close();

    #model.save('DDPG_compressor_num_action_params=' + str(env.num_action_params))
    #model.save('SAC_compressor_num_action_params=' + str(env.num_action_params))

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
    # print(" Done RL process ")
    #[15135, 2353, 48, 1790, 1382]
    #ddpg [16618, 2220, 93, 1706, 1306]


cocotb_coverage = []
norm_factor=0.0;
norm_eps=0.0;
count_width = 6
word_width = 4
c_iter=int(0);

@cocotb.coroutine
def monitor_signals(dut):
    global count_width
    
    global norm_factor
    global norm_eps
    
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_word_counter.value == 16),
            (int)(dut.rg_zero_counter.value == 64),
            (int)(dut.rg_counter.value == (2**count_width - 2)),
            (int)(dut.rg_next_count != 0),
            # (int)((dut.rg_word_counter.value == 16) and (dut.rg_counter.value == (2**count_width - 2)))]
            (int)((dut.rg_zero_counter.value == 64) and (dut.rg_next_count != 0))]
        s = ''.join(map(str, s))
        cocotb_coverage.append(s)
        norm_eps=norm_eps+1;
        norm_factor=norm_factor+1;

@cocotb.test()
def run_test(dut):
    
    #action_list = []

    global word_width
    global count_width
    
    global norm_eps
    global norm_factor

    global c_iter

    counter_iter=0;
    MAX_ITER=50;
    #reward_state=int(2);
    COVERAGE_LEN=5;
    factor_array=np.array([0.0]*COVERAGE_LEN)
    start_val=0.05
    for i in range(0, len(factor_array)):
        factor_array[i]=start_val;
    accumulated_binary_coverage=np.array([0.0]*COVERAGE_LEN)
    prev_probs=np.array([0.0]*COVERAGE_LEN)
    state=2;
    position_state=int(state);
    chosen_actions=[];
    rn_norm=0.0;
    num_a=start_val;
    num_b=start_val;

    word_width = 4 #Can be randomised to pick only from the set 1, 2, 4, 8
    count_width = 6 # count_width = random.randint(1,8)

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut)) # tracks states covered

    tb = TestBench(dut)
    tb.word_width = word_width
    tb.count_width = count_width

    N = 400


    FSM_states = ['0','1']
    
    # write_to_file('./cocotb_output.txt', [len(FSM_states)])
    while(counter_iter<MAX_ITER):
        
        parent_conn, child_conn = Pipe()
        rl_process = Process(target=rl_run, args=(child_conn,))
        rl_process.start()
        COVERAGE_LEN=int(parent_conn.recv())
        NUM_EPISODES = int(parent_conn.recv()[0])
        parent_conn.send([len(FSM_states)])

        all_labels=range(COVERAGE_LEN);
        all_labels=[str(i) for i in all_labels]

        if(counter_iter%3==0):
            counter_iter=int(0);
            for g in range(0,len(accumulated_binary_coverage)):
                accumulated_binary_coverage[g]=0.0;

        print("factor_array=",factor_array)

        if(counter_iter>0):
            probabs=accumulated_binary_coverage/norm_factor
            #probabs=-1*np.exp(-probabs/(1/COVERAGE_LEN))*np.log(probabs)
            probabs=-1*((1-probabs)**2)*np.log(probabs)
            probabs=probabs/np.sum(probabs)
            print("probabs_before=",probabs)
            probabs=probabs*factor_array;
            probabs=probabs/np.sum(probabs)
            print("probabs_after=",probabs)
            #probabs=np.exp(6*probabs);
            #probabs=probabs/np.sum(probabs);
            state_chosen=choice(all_labels,1,p=probabs,replace=False)[0];
            #position_state=all_labels.index(state_chosen);
            position_state=int(state);
            print("position_state_rewarded=",position_state)
            #reward_state=position_state;

            for i in range(0,len(accumulated_binary_coverage)):
                prev_probs[i]=accumulated_binary_coverage[i]/norm_factor;

        for n1 in range(NUM_EPISODES):
            print("-----------------------------------------------")
            print("Epsiode number: ", n1)


            norm_eps=0;
            cocotb_coverage.clear()
            history = ''

            # get action
            print('waiting for RL action', i)
            Z = parent_conn.recv()
            # Z = ['0.512462424523714', '0.9434345122764985', '1.0']
            
            
            '''
            if(counter_iter==0):
                Z=[0]*len(Z);
                for i in range(len(Z)):
                    Z[i]=(int)(random.random() * 100) / 100.
            '''

            Z = [float(i) for i in Z]
            print("action: ", Z)

            chosen_actions.append(Z[0])
            file3 = open("results_sac_2knob_250eps_chosen_actions", "a")
            file3.write(str(Z[0]))
            file3.write("\n");
            ##############################################
            # comment this block if design config params are not in action space
            '''
            count_width = math.ceil(Z[-2] * 8)
            if(count_width==0):
                count_width = 1
            print('count width', count_width)
            tb.count_width = count_width

            N = math.ceil(Z[-1] * 10) # total number of elements in activation map
            if(N == 0):
                N += 1
            N *= 100
            print('N =', N)

            Z = Z[:-2]
            '''
            ##############################################

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

            

            # write to a file the coverage, reward, etc.
            # print('cocotb', len(cocotb_coverage))
            parent_conn.send(cocotb_coverage)
            
            if(counter_iter==0 and n1==0):
                rn_norm=((rn_norm*n1)+norm_eps)/(n1+1);
            
            parent_conn.send([norm_eps,rn_norm])            
            print("norm_eps=",norm_eps)
            parent_conn.send(position_state)

            

            
            if(n1==(NUM_EPISODES-1)):    
                run_binary_coverage=parent_conn.recv()
                

                #print("1)",run_binary_coverage)
                run_binary_coverage=np.array(run_binary_coverage)
                #print("2)",run_binary_coverage)
                accumulated_binary_coverage=accumulated_binary_coverage+run_binary_coverage;
                #print("3)acc=",accumulated_binary_coverage)
                curr_probs=accumulated_binary_coverage/norm_factor;

                if(counter_iter>0):
                    f1=((curr_probs[position_state]-prev_probs[position_state])/prev_probs[position_state]);
                    f1=10*f1-np.log(99);
                    f1=1/(1+np.exp(-1*f1));
                    factor_array[position_state]=f1;
                    print(curr_probs[position_state],prev_probs[position_state],",arg=",f1,",position_state=",position_state)

                file1 = open("results_state2_comp_sac250_tuning_all", "a")
                file2 = open("results_state2_comp_sac250_tuning_probs", "a")
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
        c_iter=int(c_iter+1);
        print("norm_factor=",norm_factor)
    tb.stop()
    yield RisingEdge(dut.CLK)
