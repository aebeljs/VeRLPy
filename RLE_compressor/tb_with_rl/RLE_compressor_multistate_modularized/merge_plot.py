import matplotlib.pyplot as plt
import os
import sys
import ast
import numpy as np

if len(sys.argv) < 2:
    print('Usage: python ' + sys.argv[0] + ' test.log')
    sys.exit(0)

log_file = sys.argv[1]
file_name = os.path.basename(log_file)
file_name = os.path.splitext(file_name)[0]

suffix = '_' + file_name.split('_')[0]
file = open(log_file, 'r')

log_file_1 = sys.argv[2]
file_name_1 = os.path.basename(log_file_1)
file_name_1 = os.path.splitext(file_name_1)[0]

suffix_1 = '_' + file_name_1.split('_')[0]

file_1 = open(log_file_1, 'r')

for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 3):
        continue
    if((components[1] == 'INFO') and (components[2] == 'CONFIG')):
        suffix += '_' + components[3] + '=' + components[4]

for line in file_1:
    components_1 = line.split('|')
    components_1 = [s.strip().rstrip() for s in components_1]
    if(len(components_1) < 3):
        continue
    if((components_1[1] == 'INFO') and (components_1[2] == 'CONFIG')):
        suffix_1 += '_' + components_1[3] + '=' + components_1[4]

data = 0
data_1 = 0
x_range = 0
x_range_1 = 0

file.seek(0)
for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 5):
        continue
    if((components[1] == 'INFO') and (components[2] == 'RL') and (components[3] == 'result') and (components[4] == 'total_binary_coverage')):
        data = ast.literal_eval(components[5])
        x_range = list(range(len(data)))
        plt.vlines(x_range, 0, data, color='C0', lw=4)
        for a, b in zip(x_range, data):
            plt.text(a, b, str(b), ha='center')
        plt.grid()
        # plt.xticks(list(range(len(data))), rotation=90)
        plt.xticks(list(range(len(data))))
        plt.xlabel('Events')
        plt.tight_layout()
        plt.title("Histogram of individual event coverage\n")
        plt.savefig('./hist_of_binary_coverage' + suffix + '.png', bbox_inches='tight')
        plt.close()
        break

file_1.seek(0)
for line in file_1:
    components_1 = line.split('|')
    components_1 = [s.strip().rstrip() for s in components_1]
    if(len(components_1) < 5):
        continue
    if((components_1[1] == 'INFO') and (components_1[2] == 'RL') and (components_1[3] == 'result') and (components_1[4] == 'total_binary_coverage')):
        data_1 = ast.literal_eval(components_1[5])
        x_range_1 = list(range(len(data_1)))
        plt.vlines(x_range_1, 0, data_1, color='C0', lw=4)
        for a, b in zip(x_range_1, data_1):
            plt.text(a, b, str(b), ha='center')
        plt.grid()
        # plt.xticks(list(range(len(data))), rotation=90)
        plt.xticks(list(range(len(data_1))))
        plt.xlabel('Events')
        plt.tight_layout()
        plt.title("Histogram of individual event coverage\n")
        plt.savefig('./hist_of_binary_coverage' + suffix_1 + '.png', bbox_inches='tight')
        plt.close()
        break

x = np.arange(len(data))
width = 0.2
plt.bar(x-0.2, data, width, color='dodgerblue')
plt.bar(x, data_1, width, color='darkslateblue')
plt.xticks(list(range(len(data))))
plt.xlabel("Events")
plt.legend(["Random", "RL"])
plt.tight_layout()
plt.title("Histogram of individual event coverage\n")
plt.savefig('./merge_hist_of_binary_coverage.png', bbox_inches='tight')
plt.close()
 

file.seek(0)
for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 5):
        continue
    if((components[1] == 'INFO') and (components[2] == 'RL') and (components[3] == 'result') and (components[4] == 'total_coverage')):
        labels = ast.literal_eval(components[5])
        counts = ast.literal_eval(components[6])
        plt.vlines(labels, 0, counts, color='C0', lw=4)
        plt.grid()
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.title("Histogram of combination event coverage\n")
        plt.savefig('./hist_of_coverage' + suffix + '.png', bbox_inches='tight')
        plt.close()
        break

file.seek(0)
for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 5):
        continue
    if((components[1] == 'INFO') and (components[2] == 'RL') and (components[3] == 'result') and (components[4] == 'reward_plot')):
        data = ast.literal_eval(components[5])
        plt.plot(data)
        plt.xlabel('Steps')
        plt.grid()
        plt.tight_layout()
        plt.title("Reward vs steps\n")
        plt.savefig('./reward_plot' + suffix + '.png', bbox_inches='tight')
        plt.close()
        break

action_data_2 = 0
action_data_3 = 0
action_cont = 0

file.seek(0)
for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 5):
        continue
    if((components[1] == 'INFO') and (components[2] == 'cocotb') and (components[3] == 'result') and ('action_hist' in components[4])):
        i = components[4].split('_')[3]
        _type = components[4].split('_')[2]
        if(_type == 'continuous'):
            # continuous action
            range = ast.literal_eval(components[5])
            data = ast.literal_eval(components[6])
            plt.hist(data, bins=100, range=range)
            plt.tight_layout()
            plt.title('Histogram of action param ' + str(i))
            plt.savefig('./hist_of_actions' + '_param=' + str(i) + suffix + '.png', bbox_inches='tight')
            plt.close()
            action_cont = data
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
            if(i == "2"):
                action_data_2 = data
            elif(i == "3"):
                action_data_3 = data

file_1.seek(0)
for line in file_1:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 5):
        continue
    if((components[1] == 'INFO') and (components[2] == 'cocotb') and (components[3] == 'result') and ('action_hist' in components[4])):
        i = components[4].split('_')[3]
        _type = components[4].split('_')[2]
        if(_type == 'continuous'):
            # continuous action
            range = ast.literal_eval(components[5])
            data = ast.literal_eval(components[6])
            plt.hist(data, bins=100, range=range)
            plt.tight_layout()
            plt.title('Histogram of action param ' + str(i))
            plt.savefig('./hist_of_actions' + '_param=' + str(i) + suffix + '.png', bbox_inches='tight')
            plt.close()
        else:
            # discrete action
            labels_1 = ast.literal_eval(components[5])
            data_1 = ast.literal_eval(components[6])
            plt.hist(data_1, bins=100)
            plt.xticks(labels_1)
            plt.tight_layout()
            plt.title('Histogram of action param ' + str(i))
            plt.savefig('./hist_of_actions' + '_param=' + str(i) + suffix_1 + '.png', bbox_inches='tight')
            plt.close()

            x = np.array(labels_1)
            width = 0
            if(i == "2"):
                data = action_data_2
                width = 0.3
            elif(i == "3"):
                data = action_data_3
                width = 30
            hist_data = np.histogram(data,bins=len(labels_1))
            hist_data_1 = np.histogram(data_1,bins=len(labels_1))
            plt.bar(x-width, hist_data[0], width, color='dodgerblue')
            plt.bar(x, hist_data_1[0], width, color='darkslateblue')
            plt.xticks(labels_1)
            plt.xlabel("Events")
            plt.legend(["Random", "RL"])
            plt.tight_layout()
            plt.title('Histogram of action param ' + str(i))
            plt.savefig('./merge_hist_of_actions_' + str(i) + '.png', bbox_inches='tight')
            plt.close()