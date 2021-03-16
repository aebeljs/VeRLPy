import math
import random
import numpy as np
# import matplotlib
# import matplotlib.pyplot as plt
from collections import namedtuple
from itertools import count

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

# RL  objects
Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward'))

class ReplayMemory(object):
    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = []
        self.position = 0

    def push(self, *args):
        """Saves a transition."""
        if len(self.memory) < self.capacity:
            self.memory.append(None)
        self.memory[self.position] = Transition(*args)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)

class DQN(nn.Module):
    def __init__(self, N_state, N_action):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(N_state + N_action, 32)
        self.fc2 = nn.Linear(32, 32)
        self.fc3 = nn.Linear(32, 32)
        # self.fc4 = nn.Linear(8, 8)
        # self.fc5 = nn.Linear(8, 8)
        # self.fc6 = nn.Linear(3, 3)
        self.head = nn.Linear(32, 1)

    # Called with either one element to determine next action, or a batch
    # during optimization. Returns tensor([[left0exp,right0exp]...]).
    def forward(self, x):
        x = F.relu(self.fc1(x))
        # x = torch.sigmoid(self.fc1(x))
        # x = torch.sigmoid(self.fc2(x))
        # x = torch.sigmoid(self.fc3(x))
        # x = torch.sigmoid(self.fc4(x))
        # x = torch.sigmoid(self.fc5(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        # x = F.relu(self.fc6(x))
        # return self.head(x.view(x.size(0), -1))
        x = self.head(x)
        return x

class State:
    def __init__(self, data):
        # vector denoting the state
        self.data = data

class Action:
    def __init__(self, data):
        self.data = data
