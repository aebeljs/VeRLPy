# VeRLPy
** **Under Construction** **

[VeRLPy](https://arxiv.org/abs/2108.03978) is an open-source python library developed to improve the digital hardware verification process by using Reinforcement Learning (RL). It provides a generic [Gym](https://gym.openai.com/) environment implementation for building [cocotb](https://docs.cocotb.org/en/stable/)-based testbenches for verifying any hardware design.

## Installation
The easiest way to start using VeRLPy is to install it using `pip install verlpy`

VeRLPy is currently dependent on OpenAI [Gym](https://gym.openai.com/), [cocotb](https://docs.cocotb.org/en/stable/) and [Stable Baselines3](https://stable-baselines3.readthedocs.io/en/master/). These packages should get installed alongside VeRLPy when installing using `pip`. For running the verification, a simulator compatible with cocotb is additionally required. Please refer to the official  [cocotb](https://docs.cocotb.org/en/stable/) documentation to set this up.

## Usage Guide
Having familiarity with [cocotb](https://docs.cocotb.org/en/stable/), OpenAI [Gym](https://gym.openai.com/) and [this whitepaper on VeRLPy](https://arxiv.org/abs/2108.03978) will be very beneficial to get started with the VeRLPy library.

The hardware design provided in Verilog or VHDL is simulated by cocotb using the chosen simulator. VeRLPy aims to offer a clean interface for bringing RL logic into the conventional cocotb testbench while adhering to the OpenAI Gym environment structure allowing users to leverage the standard RL tools. The DUT and the verification testbench are the environment for the RL agent to act on. The agent chooses an action which is executed on the environment and the consequences of that action are informed back to the agent in terms of the state and the reward. 

### Identifying verification goals and defining the MDP

To build a testbench using VeRLPy, we need to start by defining the verification goals in terms of functional coverage. This involves identifying the events occurring in the DUT that correspond to the features that are part of the design specifications. The reward given to the RL agent will be a function of how often these events occur during the simulation.

In addition, since there is the additional RL component involved, the MDP has to be defined. This means identifying what each timestep and each episode corresponds to in terms of verification logic and input stimulus to the DUT, and what the state and the action space of the MDP represent. 

Each RL episode starts with a call to to the `reset()` function of the Gym environment. Followed by this, there are one or more calls to the `step(action)` function until `done` is returned with a value of `True` from the RL environment.  Refer to [Gym](https://gym.openai.com/) for a more detailed understanding of how the control flow occurs in a Gym environment. 

### Inheriting CocotbEnv

The library provides a Gym environment object `CocotbEnv` which can be inherited to build the verification testbench. This class has predefined functions/coroutines which interact with the RL agent to facilitate the learning process. These functions are triggered by the `reset()`, `step(action)`, `done` variable, etc. Please refer [here](https://github.com/aebeljs/VeRLPy/blob/main/src/cocotb_env.py) for more detailed explanations of these functions and their implementation details. We start with implementing this class that inherits `CocotbEnv`. 

```python
# test_my_example_design.py

import cocotb
from verlpy import CocotbEnv

class MyExampleDesignCocotbEnv(CocotbEnv):
    def __init__(self, dut, observation_space):
        super().__init__()
        self.dut = dut # DUT object used for cocotb-based verification
        self.observation_space = observation_space # state space of the RL agent

        # add here any "self." variables that need to be accessed in
        # other functions below

    @cocotb.coroutine
    def setup_rl_episode(self):
        # add here the logic to be 
        # executed on each call to reset() by the RL agent

    @cocotb.coroutine
    def rl_step(self):
        # add here the verification logic to be 
        # executed on each call to step() by the RL agent
        

    @cocotb.coroutine
    def terminate_rl_episode(self):
        # add here the logic to be executed at the end
        # of each RL episode when done == 1 for the Gym env


    def finish_experiment(self):
        # add here the logic to be executed after all
        # the episodes are completed
```
Note that all the coroutines with the deorator `cocotb.coroutine` require a `yield` statement in the body like how it is in standard cocotb testbenches.

### Instantiating the verification environment object

The functions/coroutine implementations defined in `MyExampleDesignCocotbEnv` should contain the appropriate logic that must run from the cocotb side. Once this class is defined, the cocotb test can be added to invoke the verification logic from this class. While defining this, the state space of the MDP should also be passed as an argument as shown below.

```python
# test_my_example_design.py

import cocotb
from verlpy import CocotbEnv, utils
import gym

class MyExampleDesignCocotbEnv(CocotbEnv):
    def __init__(self, dut, observation_space):
        super().__init__()
        self.dut = dut
        self.observation_space = observation_space

        # add here any "self." variables that need to be accessed in
        # other functions below

    @cocotb.coroutine
    def setup_rl_episode(self):
        # add here the logic to be 
        # executed on each call to reset() by the RL agent

    @cocotb.coroutine
    def rl_step(self):
        # add here the verification logic to be 
        # executed on each call to step() by the RL agent
        

    @cocotb.coroutine
    def terminate_rl_episode(self):
        # add here the logic to be executed at the end
        # of each RL episode when done == 1 for the Gym env


    def finish_experiment(self):
        # add here the logic to be executed after all
        # the episodes are completed

# entry point for the cocotb verification test
@cocotb.test()
def run_test(dut):
    cocotb_env = MyExampleDesignCocotbEnv(dut, gym.spaces.Discrete(1))
    # gym.spaces.Discrete(1) => Just 1 state in the state space
    yield cocotb_env.run()

    # plot the results of the verification experiment
    utils.visualize(cocotb_env.log_file_name)
```

VeRLPy also provides some plotting capabilities which can be accessed from `utils` as shown above.

### Adding coroutines to track events

The identified functional coverage events can be tracked by using cocotb coroutines like in conventional cocotb-based verification.

```python
# test_my_example_design.py

import cocotb
from verlpy import CocotbEnv, utils
import gym

class MyExampleDesignCocotbEnv(CocotbEnv):
    def __init__(self, dut, observation_space):
        super().__init__()
        self.dut = dut
        self.observation_space = observation_space

        # add here any "self." variables that need to be accessed in
        # other functions below

    @cocotb.coroutine
    def setup_rl_episode(self):
        # add here the logic to be 
        # executed on each call to reset() by the RL agent
        self.cocotb_coverage.clear() # clear last episode's coverage
        self.coverage_coroutine = cocotb.fork(monitor_signals(self.dut, self.cocotb_coverage))

    @cocotb.coroutine
    def rl_step(self):
        # add here the verification logic to be 
        # executed on each call to step() by the RL agent
        

    @cocotb.coroutine
    def terminate_rl_episode(self):
        # add here the logic to be executed at the end
        # of each RL episode when done == 1 for the Gym env

        self.coverage_coroutine.kill()


    def finish_experiment(self):
        # add here the logic to be executed after all
        # the episodes are completed

@cocotb.coroutine
def monitor_signals(dut, cocotb_coverage):
    while True:
        yield RisingEdge(dut.CLK)
        s = [(int)(dut.reg_1.value == 1),
             (int)((dut.reg_2.value) % 4 != 0),
             (int)(dut.reg_3.value == 32)]
        # Here reg_1, reg_2 and reg_3 are some
        # key registers of interest in the DUT

        s = ''.join(map(str, s))
        cocotb_coverage.append(s)

# entry point for the cocotb verification test
@cocotb.test()
def run_test(dut):
    cocotb_env = MyExampleDesignCocotbEnv(dut, gym.spaces.Discrete(1))
    # gym.spaces.Discrete(1) => Just 1 state in the state space
    yield cocotb_env.run()

    # plot the results of the verification experiment
    utils.visualize(cocotb_env.log_file_name)
```
The `monitor_signals` coroutine added above monitors the DUT for events of interest that count towards the functional coverage. The  boolean logical expressions in the list `s` above correspond to the logical expressions for identifying each event. The number of times these events occur affect the reward signal given to the RL agent. `monitor_signals` should track these events and add them to the `cocotb_coverage` attribute of the `MyExampleDesignCocotbEnv` class that we wrote. `monitor_signals` is invoked in the `setup_rl_episode` coroutine along with the clock and reset coroutines. It is passed the `cocotb_coverage` attribute as an argument. Note that `monitor_signals` is killed in the `terminate_rl_episode` coroutine at the end of each RL episode. This is important for all coroutines since it might otherwise lead to performance issues with multiple "alive" coroutines still ongoing from previous episodes.

### Configuration File
A configuration file `config.ini` needs to be provided to specify the parameter related to the simulation and the RL agent. A sample coniguration file is provided below with comments for what each section and key corresponds to.

```ini
; This section is to provide the
; main parameters for the verification runs
[main]
; number of RL steps for which the experiment is run
num_steps = 1000

; number of functional events tracked
num_events = 3

; weightage of each functional event for reward computation
reward_function = [0, 0, 1]

; set log_step as 0 for logging just aggregated results and 1 for logging details in each step
log_step = 0

; set mode as 0 to generate the random baseline without RL and 1 for using RL
mode = 1

; specify the stable_baselines3 algorithm to be used from SAC, DDPG and TD3
algorithm = SAC

; fsm_states contains the regex patterns for 
; state-based binary sequence generation
; (leave as [] unless utils.get_next_state_of_FSM() is needed in the code)
fsm_states = []

; Provide the discrete action component names here. 
; The valid dscrete value set for the specified keys
; should be given in the [discrete] section
discrete_params = ['count_width', 'fmap_len']


; This section is to provide the bounds
; of the continuous dimensions of the action space.
; If multiple dimensions are there, provide the list of bounds for each dimension
; eg: lower_bounds = [0, 0, 1] and upper_bounds = [1, 1, 3] corresponds to
; [0, 1] x [0, 1] x [1, 3] as the continuous action space
[continuous]
lower_bounds = [0, 5]
upper_bounds = [1, 7]


; This section is to provide the list of valid 
; discrete values for each discrete action
; component named in discrete_params
[discrete]
count_width = [1, 2, 3, 4, 5, 6, 7, 8]
fmap_len = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]


; This section is to provide the required
; hyperparameters of the chosen stable_baselines3 algorithm
[RL]
policy = 'MlpPolicy'
learning_starts = 100
learning_rate = 0.0003
train_freq = (1, 'episode')
verbose = 1
```
The `reward_function` key specifies how the functional events tracked in the `self.cocotb_coverage` attribute need to be rewarded for improving coverage. `reward_function` set as `[0, 0, 1]` like above implies that if the third functional event occurs during a step, a reward is given to the RL agent. Refer to the [paper](https://arxiv.org/) for the actual computation details.

The `[continuous]` and `[discrete]` sections together specify the total action space of the RL agent. The continuous dimensions of the action space based on the above configuration file is the cross product `[0, 1] x [5, 7]`. The discrete dimensions of the the action space is the cross product `{1, 2, ..., 8} x {100, 200, ..., 1000}`. Therefore the complete action space is the cross product `[0, 1] x [5, 7] x {1, 2, ..., 8} x {100, 200, ..., 1000}`.

### Filling in the verification logic

Finally, the body of each of the coroutines overriden in `MyExampleDesignCocotbEnv` need to be completed. The action suggested by the RL agent based on the `config.ini` can be accessed through the `self.continuous_actions` and `self.discrete_actions` attributes of the class. In the above example, `self.continuous_actions` will sample from `[0, 1] x [5, 7]` and `self.discrete_actions` will sample from `{1, 2, ..., 8} x {100, 200, ..., 1000}`.

The list `self.cocotb_coverage` needs to be updated with the strings corresponding to the covered events from the previous timestep of the RL episode for proper reward computation based on the reward function defined in the `config.ini` file. This update will happen on its own if `self.cocotb_coverage` is passed as the argument `cocotb_coverage` to the  `monitor_signals` coroutine defined above  Refer to the examples folder for more concrete examples on how this is done in various designs.

### Multi-step RL

VeRLPy by default assumes a single step single state MDP. If a multi-step MDP is required, it can be implemented by overriding `compute_rl_observation` function in the `MyExampleDesignCocotbEnv` class. The internal elements of the DUT that need to be tracked for computing the observation/state after each step can be done so by utilizing a separate coroutine like `monitor_signals` is used for computing the reward.

### Make file

The make file can be written like how it is done usually in cocotb testbenches. Once it is done and `make` is run, the verification simulation runs and the logs, models and plots are generated. Use the `mode` configuration parameter in `config.ini` for running the verification with/without the RL feedback.

## Citation

If you find this work useful, consider citing it with this BibTex:

## Change Log
08-08-2021 - Usage guide added
