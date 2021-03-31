import os
import shutil
from subprocess import Popen, PIPE, TimeoutExpired
import time
import matplotlib.pyplot as plt
import sys
import signal


# Test File Load Sizes
TEST_LOAD_SIZES = [128,512,2000,8000,32000]

number_of_small_files = 10
small_file_size = 128

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
        f = open(f"{PARENT_DIR}/../weakpeer_{idx}/download_folder/load_{size}","w")
        f.write("b"*size)
        f.close()


# Create test loads for client_idx
def create_small_test_loads(idx,num):
    for i in range(num):
        f = open(f"{PARENT_DIR}/../weakpeer_{idx}/download_folder/load_{i}","w")
        f.write("b"*small_file_size)
        f.close()

# Evaluation 1:
def evaluation_1():
    N = 3

    # Create peer environments
    create_strong_peers(N)
    create_weak_peers(N)
    
    # for i in range(N):
    #     create_test_loads(i)
    create_test_loads(1)
    
    # start server and client and check
    strong_peer_0 = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_0")    
    strong_peer_1 = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_1")    
    strong_peer_2 = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_2")    

    time.sleep(5)
    
    weak_peer_0 = Popen(['python','weak_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_0")
    weak_peer_1 = Popen(['python','weak_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_1")
    weak_peer_2 = Popen(['python','weak_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_2")

    time.sleep(5)

    weak_peer_0.communicate(input='download load_128\n download load_512'.encode("utf-8"))[0]
    weak_peer_2.communicate(input='download load_512'.encode("utf-8"))[0]

    time.sleep(5)

    download_completed = 0

    f0 = open(f"{PARENT_DIR}/../weakpeer_0/client_log.txt","r")
    lines0 = f0.readlines()
    f0.close()
    f2 = open(f"{PARENT_DIR}/../weakpeer_2/client_log.txt","r")
    lines2 = f2.readlines()
    f2.close()

    for j in lines0:
        try:
            if j.split(' ')[2] == "DownloadComplete:":
                download_completed += 1
        except IndexError as e:
            pass
    
    for j in lines2:
        try:
            if j.split(' ')[2] == "DownloadComplete:":
                download_completed += 1
        except IndexError as e:
            pass
    
    if download_completed == 3:
        print('Evaluation 1 Passed')
    else:
        print('Evaluation 1 Failed')

    time.sleep(5)

    strong_peer_0.kill()
    strong_peer_1.kill()
    strong_peer_2.kill()

    weak_peer_0.kill()
    weak_peer_1.kill()
    weak_peer_2.kill()

    # Clean up
    delete_strong_peers(N)
    delete_weak_peers(N)

# Evaluation 2:
def evaluation_2():

    #########################################1 client download###################################
    # # change between topolgy by changing the config.json
    # N = 10

    # # Create peer environments
    # create_strong_peers(N)
    # create_weak_peers(N)

    # create_small_test_loads(1,number_of_small_files)
    
    # time.sleep(5)

    # # start server and client and check
    # strong_peer_processes = []
    # for i in range(N):
    #     temp_process = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_{i}")
    #     strong_peer_processes.append(temp_process)    
     
    # time.sleep(5)

    # weak_peer_processes = []
    # for i in range(N):
    #     temp_process = Popen(['python','weak_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_{i}")
    #     weak_peer_processes.append(temp_process)    

    # time.sleep(5)
    # print("waiting for responses")

    # inputs = " ".join([f'download load_{i}\n' for i in range(number_of_small_files)])
    # weak_peer_processes[0].communicate(input=inputs.encode("utf-8"))[0]

    # print("done waiting for responses")

    # download_completed = 0

    # f0 = open(f"{PARENT_DIR}/../weakpeer_0/client_log.txt","r")
    # lines0 = f0.readlines()
    # f0.close()

    # for j in lines0:
    #     try:
    #         if j.split(' ')[2] == "DownloadComplete:":
    #             download_completed += 1
    #     except IndexError as e:
    #         pass
    
    # if download_completed == number_of_small_files:
    #     print("Passed")

    # for p in strong_peer_processes:
    #     p.kill()
    
    # for p in weak_peer_processes:
    #     p.kill()

    #########################################2 client download###################################
    # # change between topolgy by changing the config.json

    # number_of_downloading_clients = 2
    # N = 10

    # # Create peer environments
    # create_strong_peers(N)
    # create_weak_peers(N)

    # create_small_test_loads(number_of_downloading_clients,number_of_small_files)
    
    # time.sleep(5)

    # # start server and client and check
    # strong_peer_processes = []
    # for i in range(N):
    #     temp_process = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_{i}")
    #     strong_peer_processes.append(temp_process)    
     
    # time.sleep(5)

    # weak_peer_processes = []
    
    # for i in range(N):
    #     temp_process = Popen(['python','weak_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_{i}")
    #     weak_peer_processes.append(temp_process)    
    

    # time.sleep(5)
    # print("waiting for responses")

    # inputs1 = " ".join([f'download load_{i}\n' for i in range(0,5)])
    # inputs2 = " ".join([f'download load_{i}\n' for i in range(5,10)])
    # weak_peer_processes[0].communicate(input=inputs1.encode("utf-8"))[0]
    # weak_peer_processes[1].communicate(input=inputs2.encode("utf-8"))[0]
    
    # time.sleep(5)
    # print("done waiting for responses")

    # download_completed = 0

    # f0 = open(f"{PARENT_DIR}/../weakpeer_0/client_log.txt","r")
    # lines0 = f0.readlines()
    # f0.close()

    # for j in lines0:
    #     try:
    #         if j.split(' ')[2] == "DownloadComplete:":
    #             download_completed += 1
    #     except IndexError as e:
    #         pass
    
    # f1 = open(f"{PARENT_DIR}/../weakpeer_1/client_log.txt","r")
    # lines1 = f1.readlines()
    # f1.close()

    # for j in lines1:
    #     try:
    #         if j.split(' ')[2] == "DownloadComplete:":
    #             download_completed += 1
    #     except IndexError as e:
    #         pass
    
    # if download_completed == number_of_small_files:
    #     print("Passed")
    # else:
    #     print("Failed")

    # for p in strong_peer_processes:
    #     p.kill()
    
    # for p in weak_peer_processes:
    #     p.kill()
    
    #########################################4 client download###################################

    # # change between topolgy by changing the config.json

    # number_of_downloading_clients = 4
    # N = 10

    # # Create peer environments
    # create_strong_peers(N)
    # create_weak_peers(N)

    # create_small_test_loads(number_of_downloading_clients,number_of_small_files)
    
    # time.sleep(5)

    # # start server and client and check
    # strong_peer_processes = []
    # for i in range(N):
    #     temp_process = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_{i}")
    #     strong_peer_processes.append(temp_process)    
     
    # time.sleep(5)

    # weak_peer_processes = []
    
    # for i in range(N):
    #     temp_process = Popen(['python','weak_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_{i}")
    #     weak_peer_processes.append(temp_process)    
    

    # time.sleep(5)
    # print("waiting for responses")

    # inputs1 = " ".join([f'download load_{i}\n' for i in range(0,2)])
    # inputs2 = " ".join([f'download load_{i}\n' for i in range(2,4)])
    # inputs3 = " ".join([f'download load_{i}\n' for i in range(4,6)])
    # inputs4 = " ".join([f'download load_{i}\n' for i in range(6,10)])
    # weak_peer_processes[0].communicate(input=inputs1.encode("utf-8"))[0]
    # weak_peer_processes[1].communicate(input=inputs2.encode("utf-8"))[0]
    # weak_peer_processes[2].communicate(input=inputs3.encode("utf-8"))[0]
    # weak_peer_processes[3].communicate(input=inputs4.encode("utf-8"))[0]
    
    # time.sleep(5)
    # print("done waiting for responses")

    # download_completed = 0

    # for i in range(number_of_downloading_clients):
    #     f0 = open(f"{PARENT_DIR}/../weakpeer_{i}/client_log.txt","r")
    #     lines0 = f0.readlines()
    #     f0.close()

    #     for j in lines0:
    #         try:
    #             if j.split(' ')[2] == "DownloadComplete:":
    #                 download_completed += 1
    #         except IndexError as e:
    #             pass
    
    # if download_completed == number_of_small_files:
    #     print("Passed")
    # else:
    #     print("Failed")

    # for p in strong_peer_processes:
    #     p.kill()
    
    # for p in weak_peer_processes:
    #     p.kill()

    
    #########################################8 client download###################################

    # change between topolgy by changing the config.json

    number_of_downloading_clients = 8
    N = 10

    # Create peer environments
    create_strong_peers(N)
    create_weak_peers(N)

    create_small_test_loads(number_of_downloading_clients,number_of_small_files)
    
    time.sleep(5)

    # start server and client and check
    strong_peer_processes = []
    for i in range(N):
        temp_process = Popen(['python','strong_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../strongpeer_{i}")
        strong_peer_processes.append(temp_process)    
     
    time.sleep(5)

    weak_peer_processes = []
    
    for i in range(N):
        temp_process = Popen(['python','weak_peer.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=f"{PARENT_DIR}/../weakpeer_{i}")
        weak_peer_processes.append(temp_process)    
    

    time.sleep(5)
    print("waiting for responses")

    inputs1 = " ".join([f'download load_{i}\n' for i in range(0,1)])
    inputs2 = " ".join([f'download load_{i}\n' for i in range(1,2)])
    inputs3 = " ".join([f'download load_{i}\n' for i in range(2,3)])
    inputs4 = " ".join([f'download load_{i}\n' for i in range(3,4)])
    inputs5 = " ".join([f'download load_{i}\n' for i in range(4,5)])
    inputs6 = " ".join([f'download load_{i}\n' for i in range(5,6)])
    inputs7 = " ".join([f'download load_{i}\n' for i in range(6,7)])
    inputs8 = " ".join([f'download load_{i}\n' for i in range(7,10)])
    weak_peer_processes[0].communicate(input=inputs1.encode("utf-8"))[0]
    weak_peer_processes[1].communicate(input=inputs2.encode("utf-8"))[0]
    weak_peer_processes[2].communicate(input=inputs3.encode("utf-8"))[0]
    weak_peer_processes[3].communicate(input=inputs4.encode("utf-8"))[0]
    weak_peer_processes[4].communicate(input=inputs5.encode("utf-8"))[0]
    weak_peer_processes[5].communicate(input=inputs6.encode("utf-8"))[0]
    weak_peer_processes[6].communicate(input=inputs7.encode("utf-8"))[0]
    weak_peer_processes[7].communicate(input=inputs8.encode("utf-8"))[0]
    
    time.sleep(5)
    print("done waiting for responses")

    download_completed = 0

    for i in range(number_of_downloading_clients):
        f0 = open(f"{PARENT_DIR}/../weakpeer_{i}/client_log.txt","r")
        lines0 = f0.readlines()
        f0.close()

        for j in lines0:
            try:
                if j.split(' ')[2] == "DownloadComplete:":
                    download_completed += 1
            except IndexError as e:
                pass
    
    if download_completed == number_of_small_files:
        print("Passed")
    else:
        print("Failed")

    for p in strong_peer_processes:
        p.kill()
    
    for p in weak_peer_processes:
        p.kill()
    

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