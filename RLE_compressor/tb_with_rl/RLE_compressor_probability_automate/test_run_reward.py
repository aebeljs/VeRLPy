def flip_bit(state, index):
    if(state[index]):
        state[index]=int(0);
    else:
        state[index]=int(1);
    return state;

def get_reward_based_on_states_visited(coverage,chosen_states,rare_states,dict_states):
    
    #print("NUM_EPISODES=");print(NUM_EPISODES);
    
    
    NUM_EPISODES=750;
    num_states=[];
    for states in chosen_states:
        int_states=list(map(int, states))
        num_states.append(int_states);
    print("chosen states=")
    print(chosen_states)
    desired_state=num_states[len(num_states)-1];
    print(desired_state)
    if(chosen_states[len(chosen_states)-1] in rare_states):
        c_state=num_states[len(chosen_states)-1]; 
        for i in range(0,len(chosen_states)):
            derived_state1=flip_bit(c_state[:],i);
            derived_state=''.join(map(str, derived_state1))
            if((derived_state not in dict_states)):
                if(derived_state1 not in num_states):
                    num_states.append(derived_state1);
            else:
                if((dict_states[derived_state]<NUM_EPISODES) and (derived_state1 not in num_states)):
                    num_states.append(derived_state1);
                
    print("num_states=");print(num_states);
    reward = 0
    for visited_state in coverage:
        if(visited_state==desired_state):
            reward += 50;
        elif(visited_state in num_states):
            reward += 20;
        else:
            reward += 0;
    return reward


coverage=['0000','0001','0010','0011',
'0100','0101','0110','0111',
'1000','1001','1010','1011',
'1100','1101','1110','1111'
]
coverage1=[]
for st in coverage:
	coverage1.append(list(map(int, st)));

Q_states=[['0010', '1010']] 
rare_states=['1010'] 
used_states=[['0010'], ['0010', '1010']] 
dict_states={'0000': 962182, '0001': 3021, '0010': 1996, '0100': 4895, '0101': 8122, '1000': 112352, '1100': 2118, '1101': 2279, '1010': 1} 
chosen_states=['0010', '1010']

print("reward=")
print(get_reward_based_on_states_visited(coverage1,chosen_states,rare_states,dict_states))

