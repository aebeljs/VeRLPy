import cocotb
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from test_1state_RL_helper import *
from test_rle_compression_cocotb import *
import itertools
import matplotlib.pyplot as plt
import sys

# if gpu is to be used
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

coverage = []
NUM_EPISODES = 1000

@cocotb.coroutine
def monitor_signals(dut):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.rg_word_counter.value == 16),
            (int)(dut.rg_zero_counter.value == 64),
            (int)(dut.rg_counter.value == (2**count_width - 2)),
            (int)(dut.rg_next_count != 0)]
        coverage.append(s)

@cocotb.test()
def run_test(dut):
    CAP = 1000
    global NUM_EPISODES
    BATCH_SIZE = 8
    ETA = 1e-4
    global EPS_START
    global EPS_DECAY
    global EPS_END
    EPS_START = 0.9
    EPS_END = 0.05
    EPS_DECAY = 800
    TARGET_UPDATE = 5
    N_state = 0
    N_action = 1
    replay_buffer = ReplayMemory(CAP)
    init_state = State([])
    rare_threshold = max(0.01*NUM_EPISODES,20);

    action_list = []
    policy_net = DQN(N_state, N_action).to(device)

    for param in policy_net.parameters():
        nn.init.normal_(param)
    target_net = DQN(N_state, N_action).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = optim.SGD(policy_net.parameters(), lr=ETA) # no weight_decay as we want it to overfit in this case
    criterion = nn.MSELoss()

    N = 800 # total number of elements in activation map
    I = 5
    for i in range(0, N - I):
        action_list.append(i)
    action_tensor = torch.FloatTensor(action_list).reshape((len(action_list), 1))
    # normalize
    mean = torch.mean(action_tensor)
    std = torch.std(action_tensor)
    norm_action_tensor = (action_tensor - mean) / std

    global word_width
    global count_width

    word_width = 4
    #count_width = random.randint(1,8)
    count_width = 6

    #word_width = 4 #Can be randomised to pick only from the set 1, 2, 4, 8

    #count_width = 6 # count_width = random.randint(1,8)
    counter=0;
    Q_states=[];
    rare_states=[];
    used_states=[];
    dict_states={};
    histogram_list=[];
    random_hist={};
    chosen_states=[];
    chosen_actions_all=[];

    while(len(Q_states)!=0 or counter==0):
                    
        cocotb.fork(clock_gen(dut.CLK))
        cocotb.fork(monitor_signals(dut)) # tracks states covered

        chosen_actions = []
        coverage_list = []
        curr_state = init_state

        tb = TestBench(dut)
        tb.word_width = word_width
        tb.count_width = count_width

        suffix = "Iteration_num="+str(counter)+"_N=" + str(N) + ",I=" + str(I) + ",numEps=" + str(NUM_EPISODES) + ",word_w=" + str(word_width) + ",count_w=" + str(count_width)
        
        print("suffix=");print(suffix);
        if(counter>0):
            Q_states.pop(0);

        Q_val_list = []

        suffix1 = "_none_"

        for i in range(NUM_EPISODES):
            #1print("-----------------------------------------------")
            print("Epsiode number: ", i)

            # reset the DUT
            dut.RST_N <= 0
            yield Timer(2)
            dut.RST_N <= 1

            #word_width = 4
            #count_width = random.randint(1,8)

            coverage.clear()

            start_comp = start_compression(tb,word_width,count_width)
            for t in start_comp:
                yield tb.input_drv.send(t)
            yield RisingEdge(dut.CLK)
            yield RisingEdge(dut.CLK)

            # get action
            Z=1;

            if(counter==0):
                Z =  random.choice(action_list)
            else:
                Z = get_action(curr_state, target_net, norm_action_tensor, i + 1)
                Z = (int)(Z * std + mean)
                
            #1print("action: ", Z)

            chosen_actions.append(Z)

            # take action
            # number of non-zero activation map elements at the start
            n = 0
            while(n < I):
                if(dut.RDY_ma_get_input == 1):
                    input_gen = random_input_gen(tb)
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

            # RL generated number of consecutive 0s
            n=0
            while(n < Z):
                # generate consecutive 0s
                if(dut.RDY_ma_get_input == 1):
                    input_gen = zero_input_gen(tb)
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

            # remaining non-zero elements in the activation map
            n=0
            while( n < N - Z - I):
                if(dut.RDY_ma_get_input == 1):
                    input_gen = random_input_gen(tb)
                    for t in input_gen:
                        yield tb.input_drv.send(t)
                    n = n + 1
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

            # calculate the reward
            coverage.sort()
            # set_coverage has the set of states covered
            #set_coverage = list(coverage for coverage,_ in itertools.groupby(coverage))
            coverage_list = coverage_list + coverage
            coverage.clear();

            #1print("last coverage: ", set_coverage)

            if(counter>0):
                reward = get_reward_based_on_states_visited(coverage, chosen_states, rare_states, dict_states, random_hist)
                #1print("reward: ", reward)

                action_taken, next_state = Z, State([])

                # store in replay buffer
                replay_buffer.push(curr_state, action_taken, next_state, reward)

                curr_state = next_state

                # optimize the network
                if len(replay_buffer) < BATCH_SIZE:
                    continue
                transitions = replay_buffer.sample(BATCH_SIZE)
                batch = Transition(*zip(*transitions))
                action_batch = torch.FloatTensor(batch.action).reshape(len(batch.action), -1)
                reward_batch = torch.FloatTensor(batch.reward).reshape(len(batch.reward), -1)
                '''
                if (i + 1) % 20 == 0:
                    print("actions :\n", action_batch)
                    print("rewards :\n", reward_batch)
                '''
                policy_net.train()
                optimizer.zero_grad()
                # run the batch through the net
                norm_action_batch = (action_batch - mean) / std
                Q_values = policy_net(norm_action_batch)

                '''
                if (i + 1) % 20 == 0:
                    print("net_Qs :\n", Q_values)
                '''

                loss = criterion(Q_values, reward_batch)
                #1print("loss: ", loss)
                loss.backward()

                # clamp gradients values
                # for param in policy_net.parameters():
                #     param.grad.data.clamp_(-1, 1)

                '''
                if (i + 1) % 20 == 0:
                    print("head weights: ", policy_net.head.weight)
                    print("head grad: ", policy_net.head.weight.grad)
                '''

                optimizer.step()

                '''
                if (i + 1) % 20 == 0:
                    print("updated head weights: \n", policy_net.head.weight)
                    print("updated net_Qs: \n", policy_net(norm_action_batch))
                '''

                if (i % TARGET_UPDATE) == 0:
                    target_net.load_state_dict(policy_net.state_dict())

        if(counter>0):
            #1print("Learned Q function:")
            for x_ in range(len(action_tensor)):
                test_ = torch.ones((1))
                test_[0] = (x_ - mean) / std
                #1print(test_, target_net(test_))

        tb.stop()
        #suffix1 = "_iteration_num="+str(counter)+"_"; #change this
        suffix1="_";
        from collections import Counter
        # plot results
        chosen_actions_all.extend(chosen_actions);

        state_list = []
        for cov in coverage_list:
            x = ''.join(map(str, cov))
            state_list.append(x)
        state_list.sort()
        
        labels = Counter(state_list).keys() # equals to list(set(words))
        counts = Counter(state_list).values() # counts the elements' frequency
        raw_data = Counter(state_list)
        print("counter=");print(counter)
        print("labels,counts=")
        print(labels,counts)
        '''
        plt.hist(state_list)
        plt.title("1 state RL - Histogram of covered states\n" + "Reward scheme: "+suffix1)
        plt.savefig('./hist_of_coverage'+suffix1 + suffix + '.png')
        plt.close()
        '''
        histogram_list.append(labels);histogram_list.append(counts);

        if(counter==0):
            #count_labels=int(0);
            for label in labels:
                if(raw_data[label]<((counter+1)*NUM_EPISODES)):#NUM_EPISODES
                    if(raw_data[label]<rare_threshold):
                        rare_states.append(label);
                    lst=[];lst.append(label);
                    if(lst not in Q_states):
                        Q_states.append(lst);
        else:
            for label in labels:
                if(not(label in dict_states)):
                    #need to change above statement
                    if(raw_data[label]<rare_threshold):
                        rare_states.append(label);
                    lst=chosen_states[:];lst.append(label);
                    if(lst not in Q_states and (lst not in used_states)):
                        Q_states.append(lst);



        for label in labels:
            if(label in dict_states): #need to change
                dict_states[label]=(dict_states[label]+raw_data[label]);
            else:
                dict_states[label]=raw_data[label];

        if(counter==0):
            random_hist=dict_states.copy();
        '''
        for qstates in Q_states:
            if(dict_states[qstates[len(qstates)-1]]>(NUM_EPISODES*0.5)):
                valid_states[]
        '''
        
        while(len(Q_states)>0 and dict_states[(Q_states[0])[len(Q_states[0])-1]]>=((counter+1)*NUM_EPISODES)):
            Q_states.pop(0);#NUM_EPISODES
        if(len(Q_states)>0):
            chosen_states=Q_states[0];
            used_states.append(chosen_states);

        print("Q_states, rare_states, used_States, dict_States, chosen_states=")
        print(Q_states)
        print(rare_states) 
        print(used_states) 
        print(dict_states) 
        print( chosen_states)
        counter=counter+1;

    print("histogram_list=")
    print(histogram_list)
    print("dict_states=")
    print(dict_states)

    plt.hist(chosen_actions_all)
    plt.title("1 state RL - Histogram of consecutive zeros in the activation map\n" + "Reward scheme:"+suffix1)
    plt.savefig('./hist_of_actions'+suffix1 + suffix + '.png')
    plt.close()

def get_action(curr_state, net, action_tensor, steps_done):
    """
    returns the number of consecutive zeros as per current policy
    """
    # append state data to action data first if required
    sample = random.random()
    # schedule the epsilon
    eps_threshold = EPS_END + (EPS_START - EPS_END) * \
        math.exp(-1. * steps_done / EPS_DECAY)
    #print("epsilon: ", eps_threshold)

    # choose epsilon-greedily
    if(sample < eps_threshold):
        x = random.choice(list(action_tensor))
        #print("random choice", x)
        return x
    with torch.no_grad():
        outputs = net(action_tensor)
        best_action = action_tensor[torch.argmax(outputs).item(), :].item()
        #print("best choice", best_action)
        return best_action

def get_reward_based_on_states_visited(coverage,chosen_states,rare_states,dict_states, random_hist):
    
    #print("NUM_EPISODES=");print(NUM_EPISODES);
    num_states=[];
    for state in chosen_states:
        int_state=list(map(int, state))
        num_states.append(int_state);
    #print("chosen states=")
    #print(chosen_states)
    desired_state=num_states[len(num_states)-1];
    if(chosen_states[len(chosen_states)-1] in rare_states):
        c_state=num_states[len(chosen_states)-1]; 
        for i in range(0,len(chosen_states)):
            derived_state1=flip_bit(c_state[:],i);
            derived_state=''.join(map(str, derived_state1))
            if((derived_state not in dict_states)):
                if(derived_state1 not in num_states):
                    num_states.append(derived_state1);
            elif(derived_state in random_hist):
                if((random_hist[derived_state]<NUM_EPISODES) and (derived_state1 not in num_states)):
                    num_states.append(derived_state1);
            else:
                if((dict_states[derived_state]<NUM_EPISODES) and (derived_state1 not in num_states)):
                    num_states.append(derived_state1);
                
    #print("num_states=");print(num_states);
    reward = 0
    for visited_state in coverage:
        if(visited_state==desired_state):
            reward += 50;
        elif(visited_state in num_states):
            reward += 20;
        else:
            reward += 0;
    return reward

def flip_bit(state, index):
    if(state[index]):
        state[index]=int(0);
    else:
        state[index]=int(1);
    return state;