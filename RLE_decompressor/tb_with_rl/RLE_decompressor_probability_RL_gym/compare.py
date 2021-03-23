import json

with open('gym_action.txt', 'r') as file:
     gym_action = json.load(file) # use `json.loads` to do the reverse
     file.close()

with open('gym_coverage.txt', 'r') as file:
     gym_coverage = json.load(file) # use `json.loads` to do the reverse
     file.close()

with open('action.txt', 'r') as file:
     action = json.load(file) # use `json.loads` to do the reverse
     file.close()

with open('coverage.txt', 'r') as file:
     coverage = json.load(file) # use `json.loads` to do the reverse
     file.close()

print(gym_action == action)
print(gym_coverage == coverage)
list_1 = gym_coverage['1']
list_2 = coverage['1']
print(len(list_1))
print(len(list_2))
