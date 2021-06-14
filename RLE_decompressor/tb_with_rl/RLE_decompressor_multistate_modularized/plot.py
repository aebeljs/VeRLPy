import matplotlib.pyplot as plt
import os
import sys
import ast

if len(sys.argv) < 2:
    print('Usage: python ' + sys.argv[0] + ' test.log')
    sys.exit(0)

log_file = sys.argv[1]
file_name = os.path.basename(log_file)
file_name = os.path.splitext(file_name)[0]

suffix = ''
file = open(log_file, 'r')

for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 3):
        continue
    if((components[1] == 'INFO') and (components[2] == 'CONFIG')):
        suffix += '_' + components[3] + '=' + components[4]

file.seek(0)
for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 5):
        continue
    if((components[1] == 'INFO') and (components[2] == 'RL') and (components[3] == 'result') and (components[4] == 'total_binary_coverage')):
        data = ast.literal_eval(components[5])
        plt.vlines(list(range(len(data))), 0, data, color='C0', lw=4)
        plt.grid()
        plt.xticks(list(range(len(data))), rotation=90)
        plt.tight_layout()
        plt.title("Histogram of individual event coverage\n")
        plt.savefig('./hist_of_binary_coverage' + suffix + '.png', bbox_inches='tight')
        plt.close()
        break

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
        plt.grid()
        plt.tight_layout()
        plt.title("Reward vs step\n")
        plt.savefig('./reward_plot' + suffix + '.png', bbox_inches='tight')
        plt.close()
        break

file.seek(0)
for line in file:
    components = line.split('|')
    components = [s.strip().rstrip() for s in components]
    if(len(components) < 5):
        continue
    if((components[1] == 'INFO') and (components[2] == 'cocotb') and (components[3] == 'result') and ('action_hist' in components[4])):
        i = components[4].split('_')[2]
        if(len(components) < 7):
            # continuous action
            data = ast.literal_eval(components[5])
            plt.hist(data, bins=100, range=[0.0, 1.0])
            plt.tight_layout()
            plt.title('Histogram of action param ' + str(i))
            plt.savefig('./hist_of_actions' + '_param=' + str(i) + suffix + '.png', bbox_inches='tight')
            plt.close()
        else:
            # discrete action
            labels = ast.literal_eval(components[5])
            data = ast.literal_eval(components[6])
            plt.hist(data, bins=100, range=[min(labels), max(labels)])
            plt.tight_layout()
            plt.title('Histogram of action param ' + str(i))
            plt.savefig('./hist_of_actions' + '_param=' + str(i) + suffix + '.png', bbox_inches='tight')
            plt.close()
