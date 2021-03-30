import os
import shutil
from subprocess import Popen, PIPE
import time
import matplotlib.pyplot as plt
import sys

# Test File Load Sizes
TEST_LOAD_SIZES = [128,512,2000,8000,32000]

# Get parent directory
PARENT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_strong_peers(N):
    """
    Create N strong peers
    """
    for i in range(N):
        if not os.path.exists(f"{PARENT_DIR}/../strongpeer_{i}"):
            os.mkdir(f"{PARENT_DIR}/../strongpeer_{i}")
        if not os.path.exists(f"{PARENT_DIR}/../strongpeer_{i}/watch_folder"):
            os.mkdir(f"{PARENT_DIR}/../strongpeer_{i}/watch_folder")
        
        shutil.copyfile(f"{PARENT_DIR}/config.json", f"{PARENT_DIR}/../strongpeer_{i}/config.json")
        shutil.copyfile(f"{PARENT_DIR}/strong_peer.py", f"{PARENT_DIR}/../strongpeer_{i}/strong_peer.py")

def create_weak_peers(N):
    """
    Create N weak peers
    """
    for i in range(N):
        if not os.path.exists(f"{PARENT_DIR}/../weakpeer_{i}"):
            os.mkdir(f"{PARENT_DIR}/../weakpeer_{i}")
        if not os.path.exists(f"{PARENT_DIR}/../weakpeer_{i}/download_folder"):
            os.mkdir(f"{PARENT_DIR}/../weakpeer_{i}/download_folder")

        shutil.copyfile(f"{PARENT_DIR}/config.json", f"{PARENT_DIR}/../weakpeer_{i}/config.json")
        shutil.copyfile(f"{PARENT_DIR}/weak_peer.py", f"{PARENT_DIR}/../weakpeer_{i}/weak_peer.py")

def delete_strong_peers(N):
    """
    Delete N strong peers
    """
    for i in range(N):
        shutil.rmtree(f"{PARENT_DIR}/../strongpeer_{i}")

def delete_weak_peers(N):
    """
    Delete N weak peers
    """
    for i in range(N):
        shutil.rmtree(f"{PARENT_DIR}/../weakpeer_{i}")

# Create test loads for client_idx
def create_test_loads(idx):
    for size in TEST_LOAD_SIZES:
        f = open(f"{PARENT_DIR}/../weakpeer_{idx}/download_folder/load_{size}","wb")
        f.write(os.urandom(size))
        f.close()

# Evaluation 1:
def evaluation_1():
    N = 3

    # Create peer environments
    create_strong_peers(N)
    create_weak_peers(N)
    
    for i in range(N):
        create_test_loads(i)

     # start server and client and check
    strong_peer_1 = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_1")    
    strong_peer_2 = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_2")    
    strong_peer_3 = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_3")    

    weak_peer_1 = Popen(['python','weak_peer.py',f"download load_{TEST_LOAD_SIZES[-1]}"], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_1")
    weak_peer_2 = Popen(['python','weak_peer.py',f"download load_{TEST_LOAD_SIZES[-1]}"], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_2")
    weak_peer_3 = Popen(['python','weak_peer.py',f"download load_{TEST_LOAD_SIZES[-1]}"], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_3")

    time.sleep(10)

    strong_peer_1.kill()
    strong_peer_2.kill()
    strong_peer_3.kill()

    weak_peer_1.kill()
    weak_peer_2.kill()
    weak_peer_3.kill()

    # Clean up
    delete_strong_peers(N)
    delete_weak_peers(N)

# Evaluation 2:
def evaluation_2():
    pass

if __name__ == "__main__":
    if sys.argv[1] == "-1":
        evaluation_1()

    elif sys.argv[1] == "-2":
        evaluation_2()

    elif sys.argv[1] == "-c" and len(sys.argv) == 3:
        try: 
            N = int(sys.argv[2])
            create_strong_peers(N)
            create_weak_peers(N)
            create_test_loads(0)
        except Exception as e:
            print(e)

    elif sys.argv[1] == "-d" and len(sys.argv) == 3:
        try:
            N = int(sys.argv[2])
            delete_strong_peers(N)
            delete_weak_peers(N)
        except Exception as e:
            print(e)