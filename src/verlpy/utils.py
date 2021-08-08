import matplotlib.pyplot as plt
import os
import ast
import re

def get_next_state_of_FSM(binary_seq, patterns):
    '''
    Function for FSM-based binary sequence generation

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

def visualize(log_file):
    '''
    Function for plotting coverage, actions chosen and reward

    Inputs
    log_file  : Name of the log file which contains the information 
                from the verification run
    '''
    file_name = os.path.basename(log_file)
    file_name = os.path.splitext(file_name)[0]

    suffix = '_' + file_name
    file = open(log_file, 'r')

    for line in file:
        components = line.split('|')
        components = [s.strip().rstrip() for s in components]
        if(len(components) < 5):
            continue    
        if((components[1] == 'INFO') and (components[2] == 'RL')):
            if(components[3] == 'result'):
                if(components[4] == 'total_binary_coverage'):
                    # coverage of each functional event
                    data = ast.literal_eval(components[5])
                    x_range = list(range(len(data)))
                    plt.vlines(x_range, 0, data, color='C0', lw=4)
                    for a, b in zip(x_range, data):
                        plt.text(a, b, str(b), ha='center')
                    plt.grid()
                    plt.xticks(list(range(len(data))))
                    plt.xlabel('Events')
                    plt.tight_layout()
                    plt.title("Histogram of individual event coverage\n")
                    plt.savefig('./hist_of_coverage' + suffix + '.png', bbox_inches='tight')
                    plt.close()
                elif(components[4] == 'total_coverage'):
                    # coverage of the combinations of functional events
                    labels = ast.literal_eval(components[5])
                    counts = ast.literal_eval(components[6])
                    plt.vlines(labels, 0, counts, color='C0', lw=4)
                    plt.grid()
                    plt.xticks(rotation=90)
                    plt.tight_layout()
                    plt.title("Histogram of combination event coverage\n")
                    plt.savefig('./hist_of_combination_coverage' + suffix + '.png', bbox_inches='tight')
                    plt.close()
                elif(components[4] == 'reward_plot'):
                    # plot of reward awarded on each timestep
                    data = ast.literal_eval(components[5])
                    plt.plot(data)
                    plt.xlabel('Steps')
                    plt.grid()
                    plt.tight_layout()
                    plt.title("Reward vs steps\n")
                    plt.savefig('./reward_plot' + suffix + '.png', bbox_inches='tight')
                    plt.close()
        elif((components[1] == 'INFO') and (components[2] == 'cocotb')):
            if((components[3] == 'result') and ('action_hist' in components[4])):
                # histogram of choice of actions
                i = components[4].split('_')[3]
                _type = components[4].split('_')[2]
                if(_type == 'continuous'):
                    # continuous action
                    x_range = ast.literal_eval(components[5])
                    data = ast.literal_eval(components[6])
                    plt.hist(data, bins=100, range=x_range)
                    plt.tight_layout()
                    plt.title('Histogram of action param ' + str(i))
                    plt.savefig('./hist_of_actions' + '_param=' + str(i) + suffix + '.png', bbox_inches='tight')
                    plt.close()
                else:
                    # discrete action
                    labels = ast.literal_eval(components[5])
                    data = ast.literal_eval(components[6])
                    plt.hist(data, bins=100)
                    plt.xticks(labels)
                    plt.tight_layout()
                    plt.title('Histogram of action param ' + str(i))
                    plt.savefig('./hist_of_actions' + '_param=' + str(i) + suffix + '.png', bbox_inches='tight')
                    plt.close()