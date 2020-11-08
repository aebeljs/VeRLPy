import cocotb
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from test_1state_RL_helper import *
from test_rle_compression_cocotb import *
import itertools
import matplotlib.pyplot as plt

# if gpu is to be used
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

coverage = []

@cocotb.coroutine
def monitor_signals(dut):
    while True:
        yield RisingEdge(dut.CLK)
        # print('[SIG_MON] {0:<25} : {1}'.format('rg_next_word ', hex(dut.rg_next_word.value)))
        s = [(int)(dut.rg_word_counter.value == 16), (int)(dut.rg_zero_counter.value == 64), 0]
        zero_counter = hex(dut.rg_counter.value)
        for i in range(2, len(zero_counter)):
            if(zero_counter[i] == 'f'):
                s[2] = 1
                break
        coverage.append(s)

@cocotb.test()
def run_test(dut):
    CAP = 100
    NUM_EPISODES = 100
    BATCH_SIZE = 10
    global EPS_START
    global EPS_DECAY
    global EPS_END
    EPS_START = 0.9
    EPS_END = 0.05
    EPS_DECAY = 50
    TARGET_UPDATE = 4
    N_state = 0
    N_action = 1
    replay_buffer = ReplayMemory(CAP)
    init_state = State([])

    action_list = []
    policy_net = DQN(N_state, N_action).to(device)
    target_net = DQN(N_state, N_action).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = optim.RMSprop(policy_net.parameters())

    N = 100 # total number of elements in activation map
    I = 10 # change this later
    for i in range(I, N):
        action_list.append(i)
    action_tensor = torch.FloatTensor(action_list).reshape((len(action_list), 1))

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut))

    chosen_actions = []
    coverage_list = []
    for i in range(NUM_EPISODES):
        print("Epsiode number: ", i)
        curr_state = init_state

        # take step
        # action_taken, next_state, reward = take_step_in_env(curr_state, dut)
        # wrap this one episode inside the training loop
        tb = TestBench(dut)
        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        # print(coverage)
        coverage.clear()

        word_width = 4  #Can be randomised to pick only from the set 4, 8, 16, 32
        count_width = random.randint(1,8)
        start_comp = start_compression(tb,word_width,count_width)
        for t in start_comp:
            yield tb.input_drv.send(t)
        yield RisingEdge(dut.CLK)
        yield RisingEdge(dut.CLK)

        # generate action for agent based on curr_state
        Z = get_action(curr_state, policy_net, action_tensor, i + 1)

        chosen_actions.append(Z)
        print("action: ", Z)

        # take action
        # number of non-zero activation map elements at the start
        for n in range(I):
            if(dut.RDY_ma_get_input == 1):
                input_gen = random_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                yield RisingEdge(dut.CLK)

            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                n = n-1 ##Enabling output is not considered as new input

        print("initial done")
        # RL generated number of consecutive 0s
        for n in range(Z):
            # generate consecutive 0s
            if(dut.RDY_ma_get_input == 1):
                input_gen = zero_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                yield RisingEdge(dut.CLK)
                # fsm_states_visited.append(cocotb.fork(monitor_signals(dut)))
            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                n = n-1 ##Enabling output is not considered as new input
        print("zeros done")
        # remaining non-zero elements in the activation map
        for n in range(N - Z - I):
            if(dut.RDY_ma_get_input == 1):
                input_gen = random_input_gen(tb)
                for t in input_gen:
                    yield tb.input_drv.send(t)
                yield RisingEdge(dut.CLK)
                # fsm_states_visited.append(cocotb.fork(monitor_signals(dut)))
            elif(dut.RDY_mav_send_compressed_value == 1):
                output_enable = enable_compression_output(tb)
                for t in output_enable:
                    yield tb.input_drv.send(t)
                n = n-1 ##Enabling output is not considered as new input
        print("final done")
        end_comp = enable_end_compression(tb)
        for t in end_comp:
            yield tb.input_drv.send(t)

        for n in range(10):
            yield RisingEdge(dut.CLK)
        tb.stop()
        yield RisingEdge(dut.CLK)

        # calculate the reward
        coverage.sort()
        set_coverage = list(coverage for coverage,_ in itertools.groupby(coverage))
        coverage_list = coverage_list + set_coverage
        print("last coverage: ", set_coverage)

        reward = get_reward_based_on_states_visited(set_coverage)

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

        # run the batch through the net
        Q_values = policy_net(action_batch)
        # print(Q_values)

        # Optimize the model
        optimizer.zero_grad()
        loss = F.smooth_l1_loss(Q_values, reward_batch)

        loss.backward()
        for param in policy_net.parameters():
            param.grad.data.clamp_(-1, 1)
        optimizer.step()

        if i % TARGET_UPDATE:
            target_net.load_state_dict(policy_net.state_dict())



    # plot results
    plt.hist(chosen_actions)
    plt.title("Histogram of consecutive zeros in the activation map")
    plt.savefig('./hist_of_actions.png')
    plt.close()

    state_list = []
    for cov in coverage_list:
        x = ''.join(map(str, cov))
        state_list.append(x)

    plt.hist(state_list)
    plt.title("Histogram of covered states")
    plt.savefig('./hist_of_coverage.png')
    plt.close()

def get_action(curr_state, policy_net, action_tensor, steps_done):
    """
    returns the number of consecutive zeros as per current policy
    """
    # append state data to action data first if required
    sample = random.random()
    eps_threshold = EPS_END + (EPS_START - EPS_END) * \
        math.exp(-1. * steps_done / EPS_DECAY)
    print("epsilon: ", eps_threshold)
    if(sample < eps_threshold):
        return (int)(random.choice(list(action_tensor)))
    with torch.no_grad():
        outputs = policy_net(action_tensor)
        best_action = action_tensor[torch.argmax(outputs).item(), :].item()
        return (int)(best_action)

def get_reward_based_on_states_visited(coverage):
    reward = 0
    for visited_state in coverage:
        x = visited_state[0] + visited_state[1]
        if(x == 1):
            reward += 10
        elif(x == 2):
            reward += 20
        if(visited_state[2] == 1):
            reward += 100
    return reward
