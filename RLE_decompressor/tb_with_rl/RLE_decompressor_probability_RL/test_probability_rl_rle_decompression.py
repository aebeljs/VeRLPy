import cocotb
from test_rle_decompression_cocotb import *
import itertools
import matplotlib.pyplot as plt
import sys
from collections import defaultdict
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from test_1state_RL_helper import *

# if gpu is to be used
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

coverage = []
total_coverage = []
total_set_coverage = []
count_width = 6
word_width = 4
random.seed(1)

@coroutine
def monitor_signals(dut):
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
        coverage.append(s)
        ## ** difficult to cover
        ##rg_count_valid == False
        ##rg_word_valid == False
        ##rg_counter_valid == False
        ##rg_zero_counter == 64
        ##rg_word_counter == 16
        ## ** rg_counter == 2**count_width-2
        ## ** rg_next_count != 0
        ##rg_is_next_word == True


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
    EPS_DECAY = 500
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
    action_tensor = torch.arange(0.01, 1., 0.01)
    action_tensor = action_tensor.reshape(action_tensor.shape[0], 1)
    print(action_tensor.shape)

    # normalize
    mean = torch.mean(action_tensor)
    std = torch.std(action_tensor)
    norm_action_tensor = (action_tensor - mean) / std

    word_width = 4 #Can be randomised to pick only from the set 1, 2, 4, 8
    count_width = 6 # count_width = random.randint(1,8)

    cocotb.fork(clock_gen(dut.CLK))
    cocotb.fork(monitor_signals(dut)) # tracks states covered

    chosen_actions = []
    coverage_list = []
    curr_state = init_state

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

    suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ",word_w=" + str(word_width) + ",count_w=" + str(count_width)
    suffix1 = "_00000010"
    Q_val_list = []

    # suffix = "_m=" + str(M) + ",numEps=" + str(NUM_EPISODES)
    # suffix = "_N=" + str(N) + ",numEps=" + str(NUM_EPISODES) + ',word_width=' + str(word_width) + ',count_width=' + str(count_width)
    for i in range(NUM_EPISODES):
        print("Episode : ", i + 1)

        coverage.clear()
        activation_map.clear()
        input_list.clear()

        dut.RST_N <= 0
        yield Timer(2)
        dut.RST_N <= 1

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        # get action
        Z = get_action(curr_state, target_net, norm_action_tensor, i + 1)
        Z = (Z * std + mean)
        print("action: ", Z)

        chosen_actions.append(Z.item())

        print('Probab:', Z)

        design_config_string = count_width << 4 | word_width

        for n2 in range(N):
            if(random.random() < Z):
                # next element is 0
                activation_map.append(0)
            else:
                # next element is not 0
                activation_map.append(random.randint(1, 2**(word_width*4)))

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
        # print(input_list)
        input_list.insert(0, input_list.pop(first_compressed_zero_idx))

        ##Initial compressed input alone will have details of word width and count width
        compressed_input = input_list[0]
        for compressed_input in input_list:
            if(dut.RDY_ma_get_inputs != 1):
                yield RisingEdge(dut.RDY_ma_get_inputs)
            yield tb.input_drv.send(InputTransaction(tb,1,compressed_input))
            yield tb.input_drv.send(InputTransaction(tb,0,0))
            ##Input Randomisation
            # compressed_input = input_list[n2]
            yield RisingEdge(dut.CLK)
            yield RisingEdge(dut.CLK)

        print("Driven all inputs for this episode ")
        for delay in range(5):
            yield RisingEdge(dut.CLK)
        if(dut.RDY_ma_send_decompressed_output == 1):
            yield FallingEdge(dut.RDY_ma_send_decompressed_output)

        for delay in range(10):
            yield RisingEdge(dut.CLK)

        # process coverage of this episode here
        total_coverage.extend(coverage)

        set_coverage = list(dict.fromkeys(coverage))

        print("last coverage: ", set_coverage)
        total_set_coverage.extend(set_coverage)

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
    for x_ in range(len(norm_action_tensor)):
        test_ = norm_action_tensor[x_]
        print(test_ * std + mean, target_net(test_))

    tb.stop()
    yield RisingEdge(dut.CLK)

    plt.hist(chosen_actions)
    plt.tight_layout()
    plt.title("Stochastic input using RL- Histogram of Pr(0) in the activation map\n" + "Reward scheme:"+suffix1)
    plt.savefig('./hist_of_actions'+suffix1 + suffix + '.png', bbox_inches='tight')
    plt.close()

    total_coverage.sort()
    from collections import Counter
    labels = list(Counter(total_coverage).keys()) # equals to list(set(words))
    counts = list(Counter(total_coverage).values()) # counts the elements' frequency
    print('Coverage histogram')
    for c in range(len(labels)):
        print(labels[c], counts[c])
    # # remove 00000001 for plotting
    # for p in range(len(labels)):
    #     if labels[p] == '00000001':
    #         labels.pop(p)
    #         counts.pop(p)
    #         break
    plt.vlines(labels, 0, counts, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of covered states\n")
    plt.savefig('./hist_of_coverage' +suffix1+ suffix + '.png', bbox_inches='tight')
    plt.close()

    total_set_coverage.sort()
    labels = list(Counter(total_set_coverage).keys()) # equals to list(set(words))
    counts = list(Counter(total_set_coverage).values()) # counts the elements' frequency
    print('Set coverage histogram')
    for c in range(len(labels)):
        print(labels[c], counts[c])
    plt.vlines(labels, 0, counts, color='C0', lw=4)
    plt.grid()
    plt.xticks(rotation = 90)
    plt.tight_layout()
    plt.title("Histogram of set of covered states\n")
    plt.savefig('./hist_of_set_coverage' +suffix1+ suffix + '.png', bbox_inches='tight')
    plt.close()


def get_action(curr_state, net, action_tensor, steps_done):
    """
    returns the number of consecutive zeros as per current policy
    """
    # append state data to action data first if required
    sample = random.random()
    # schedule the epsilon
    eps_threshold = EPS_END + (EPS_START - EPS_END) * \
        math.exp(-1 * steps_done / EPS_DECAY)
    '''
    if(steps_done<(EPS_DECAY/3)):
        eps_threshold = EPS_END + (EPS_START - EPS_END) * \
        math.exp(-0.1 * steps_done / EPS_DECAY)
    '''
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
        if(visited_state == '00000010'):
            reward += 10
    return reward
