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
    NUM_EPISODES = 1000
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

    action_list = []
    policy_net = DQN(N_state, N_action).to(device)

    for param in policy_net.parameters():
        nn.init.normal_(param)
    target_net = DQN(N_state, N_action).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = optim.SGD(policy_net.parameters(), lr=ETA) # no weight_decay as we want it to overfit in this case
    criterion = nn.MSELoss()

    N = 400 # total number of elements in activation map
    I = 100
    for i in range(0, N - I):
        action_list.append(i)
    action_tensor = torch.FloatTensor(action_list).reshape((len(action_list), 1))
    # normalize
    mean = torch.mean(action_tensor)
    std = torch.std(action_tensor)
    norm_action_tensor = (action_tensor - mean) / std

    global word_width
    global count_width

    word_width = 4 #Can be randomised to pick only from the set 1, 2, 4, 8
    count_width = 6 # count_width = random.randint(1,8)

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut)) # tracks states covered

    chosen_actions = []
    coverage_list = []
    curr_state = init_state

    suffix = "_N=" + str(N) + ",I=" + str(I) + ",numEps=" + str(NUM_EPISODES) + ",word_w=" + str(word_width) + ",count_w=" + str(count_width)

    tb = TestBench(dut)
    Q_val_list = []
    for i in range(NUM_EPISODES):
        print("-----------------------------------------------")
        print("Epsiode number: ", i)

        # reset the DUT
        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        coverage.clear()

        start_comp = start_compression(tb,word_width,count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # get action
        Z = get_action(curr_state, target_net, norm_action_tensor, i + 1)
        Z = (int)(Z * std + mean)
        print("action: ", Z)

        chosen_actions.append(Z)

        # take action
        # number of non-zero activation map elements at the start
        n = 0
        while(n < I):
            if(dut.RDY_ma_get_input == 1):
                input_gen = random_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                yield RisingEdge(dut.CLK)
                n += 1

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                # n = n-1 # Enabling output is not considered as new input

        # RL generated number of consecutive 0s
        n = 0
        while(n < Z):
            # generate consecutive 0s
            if(dut.RDY_ma_get_input == 1):
                input_gen = zero_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                yield RisingEdge(dut.CLK)
                n += 1

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                # n = n-1 # Enabling output is not considered as new input

        # remaining non-zero elements in the activation map
        n = 0
        while(n < (N - Z - I)):
            if(dut.RDY_ma_get_input == 1):
                input_gen = random_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                yield RisingEdge(dut.CLK)
                n += 1

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                # n = n-1 # Enabling output is not considered as new input

        end_comp = enable_end_compression(tb)
        for t in end_comp:
            yield tb.input_drv.send(t)

        for n in range(10):
            yield RisingEdge(dut.CLK)

        yield RisingEdge(dut.CLK)

        # get transition coverage
        transition_coverage = []
        for p in range(len(coverage) - 1):
            transition = coverage[p]
            transition.append('-')
            transition = transition + coverage[p + 1]
            transition_str = ''.join(map(str, transition))
            transition_coverage.append(transition_str)

        # calculate the reward
        transition_coverage.sort()
        # set_coverage has the set of states covered
        set_coverage = list(transition_coverage for transition_coverage,_ in itertools.groupby(transition_coverage))
        coverage_list = coverage_list + set_coverage

        print("last coverage: ", set_coverage)

        reward = get_reward_based_on_states_visited(set_coverage)
        print("reward: ", reward)

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

        if (i + 1) % 20 == 0:
            print("actions :\n", action_batch)
            print("rewards :\n", reward_batch)

        policy_net.train()
        optimizer.zero_grad()
        # run the batch through the net
        norm_action_batch = (action_batch - mean) / std
        Q_values = policy_net(norm_action_batch)

        if (i + 1) % 20 == 0:
            print("net_Qs :\n", Q_values)

        loss = criterion(Q_values, reward_batch)
        print("loss: ", loss)
        loss.backward()

        # clamp gradients values
        # for param in policy_net.parameters():
        #     param.grad.data.clamp_(-1, 1)

        if (i + 1) % 20 == 0:
            print("head weights: ", policy_net.head.weight)
            print("head grad: ", policy_net.head.weight.grad)

        optimizer.step()

        if (i + 1) % 20 == 0:
            print("updated head weights: \n", policy_net.head.weight)
            print("updated net_Qs: \n", policy_net(norm_action_batch))

        if (i % TARGET_UPDATE) == 0:
            target_net.load_state_dict(policy_net.state_dict())

    print("Learned Q function:")
    for x_ in range(len(action_tensor)):
        test_ = torch.ones((1))
        test_[0] = (x_ - mean) / std
        print(test_, target_net(test_))

    tb.stop()

    # plot results
    plt.hist(chosen_actions)
    plt.title("1 state RL - Histogram of consecutive zeros in the activation map\n" + "Reward scheme: 0000-1100")
    plt.savefig('./hist_of_actions_0000-1100' + suffix + '.png')
    plt.close()

    coverage_list.sort()
    from collections import Counter
    labels = Counter(coverage_list).keys() # equals to list(set(words))
    counts = Counter(coverage_list).values() # counts the elements' frequency
    plt.vlines(labels, 0, counts, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("1 state RL - Histogram of covered state transitions\n" + "Reward scheme: 0000-1100")
    plt.savefig('./hist_of_coverage_0000-1100' + suffix + '.png')
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
    print("epsilon: ", eps_threshold)

    # choose epsilon-greedily
    if(sample < eps_threshold):
        x = random.choice(list(action_tensor))
        print("random choice", x)
        return x
    with torch.no_grad():
        outputs = net(action_tensor)
        best_action = action_tensor[torch.argmax(outputs).item(), :].item()
        print("best choice", best_action)
        return best_action

def get_reward_based_on_states_visited(coverage):
    reward = 0
    for visited_state in coverage:
        if(visited_state == '0000-1100'):
            reward += 10
        else:
            reward += 1
    return reward