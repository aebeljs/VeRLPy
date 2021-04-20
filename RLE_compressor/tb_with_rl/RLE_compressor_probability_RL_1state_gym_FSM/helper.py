import os
import fcntl
import re

def wait_till_read(filename):
    while(True):
        if(os.path.isfile(filename)):
            with open(filename, "r+") as f:
                fcntl.flock(f, fcntl.LOCK_EX) # lock to avoid concurrency issues
                content = [line.rstrip() for line in f]
                if(len(content) != 0):
                    f.truncate(0)
                    fcntl.flock(f, fcntl.LOCK_UN)
                    f.close()
                    # print(content[0])
                    print('length of content read', len(content))
                    break
                fcntl.flock(f, fcntl.LOCK_UN)
                f.close()
    return content

def write_to_file(filename, content):
    with open(filename, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX) # lock to avoid concurrency issues
        content = [str(i) for i in content]
        f.write('\n'.join(content))
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()
        print(len(content), 'written')

def match(patterns, seq):
    if((len(patterns) == 0) or (len(patterns[0]) == 0) or (len(seq) < len(patterns[0]))):
        return 0 # idle state is taken as the first state
    window = len(patterns[0])
    for state in range(len(patterns)):
        x = re.search(patterns[state], seq[-window:])
        if(x is not None):
            return state
    return 0
