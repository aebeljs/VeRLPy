def flip_bit(state, index):
    if(state[index]):
        state[index]=int(0);
    else:
        state[index]=int(1);
    return state;

def get_reward_based_on_states_visited(coverage,chosen_states,rare_states,dict_states, random_hist):
    
    #print("NUM_EPISODES=");print(NUM_EPISODES);
    NUM_EPISODES=1000;
    num_states=[];
    for state in chosen_states:
        int_state=list(map(int, state))
        num_states.append(int_state);
    #print("chosen states=")
    #print(chosen_states)
    desired_state=num_states[len(num_states)-1];
    if(chosen_states[len(chosen_states)-1] in rare_states):
        c_state=num_states[len(chosen_states)-1]; 
        for i in range(0,len(chosen_states)):
            derived_state1=flip_bit(c_state[:],i);
            derived_state=''.join(map(str, derived_state1))
            if((derived_state not in dict_states)):
                if(derived_state1 not in num_states):
                    num_states.append(derived_state1);
            elif(derived_state in random_hist):
                if((random_hist[derived_state]<NUM_EPISODES) and (derived_state1 not in num_states)):
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

dict_states={'0000': 2565275, '0001': 6700, '0010': 2439, '0100': 11085, '0101': 17989, '1000': 304686, '1010': 2, '1100': 5227, '1101': 5041}; 
random_hist={'0000': 1282667, '0001': 4016, '0010': 369, '0100': 6447, '0101': 10876, '1000': 148696, '1010': 1, '1100': 2946, '1101': 2998}
chosen_states=['1010'];
rare_states=['1010'];
coverage=[];
get_reward_based_on_states_visited(coverage,chosen_states,rare_states,dict_states, random_hist);


labels,counts=
dict_keys(['0000', '0001', '0010', '0100', '0101', '1000', '1100', '1101']) dict_values([1301088, 1876, 948, 3478, 4972, 209895, 2277, 1410])
Q_states, rare_states, used_States, dict_States, chosen_states=
[] [] [['0010']] {'0000': 2583580, '0001': 5934, '0010': 1338, '0100': 10019, '0101': 15976, '1000': 358364, '1100': 5061, '1101': 4254} ['0010']
histogram_list=
[dict_keys(['0000', '0001', '0010', '0100', '0101', '1000', '1100', '1101']), dict_values([1282492, 4058, 390, 6541, 11004, 148469, 2784, 2844]), dict_keys(['0000', '0001', '0010', '0100', '0101', '1000', '1100', '1101']), dict_values([1301088, 1876, 948, 3478, 4972, 209895, 2277, 1410])]
dict_states=
{'0000': 2583580, '0001': 5934, '0010': 1338, '0100': 10019, '0101': 15976, '1000': 358364, '1100': 5061, '1101': 4254}


last coverage:  [[0, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0], [0, 1, 0, 1], [1, 0, 0, 0]]
labels=
dict_keys(['0000', '0001', '0010', '0100', '0101', '1000', '1010', '1100', '1101'])
counts-
dict_values([3000, 2894, 150, 3000, 2894, 2999, 1, 2693, 1890])