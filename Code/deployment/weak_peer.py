import socket, select, errno
import os, time, json, hashlib, sys, datetime
from threading import Thread
from pathlib import Path
from _thread import *

# get configurations 
config = json.load(open(f"{os.path.dirname(os.path.abspath(__file__))}/config.json"))

EDGES = config['edges']
STRONG_PEERS = config['strong_peers']
WEAK_PEERS = config['weak_peers']

WEAK_PEER_ID = int(os.path.basename(Path(os.path.realpath(__file__)).parent).split('_')[1])
IP = WEAK_PEERS[WEAK_PEER_ID]['ip_address']
SERVER_PORT = WEAK_PEERS[WEAK_PEER_ID]['port']

HOST_FOLDER = WEAK_PEERS[WEAK_PEER_ID]['host_folder']

HEADER_LENGTH = config['header_length']
META_LENGTH = config['meta_length']
REDOWNLOAD_TIME = config['redownload_times']
LOG = open(f"{os.path.dirname(os.path.abspath(__file__))}/{WEAK_PEERS[WEAK_PEER_ID]['log_file']}", "a")




#################################################################HELPER FUNCTIONS###################################################################
def log_this(message):
    """
    Logs a message 
    """
    # print(msg)
    LOG.write(f"{datetime.datetime.now()} {message}\n")
    LOG.flush()

def help():
    """
    Prints out a verbose description of all available functions on the client 
    """
    print("\n*** INFO ON FUNCTIONS ***\n")
    print("[function_name] [options] [parameters] - [description]\n")
    print("get_files_list - gets the file names from all the clients\n")
    print("download <client_number> <file_name> ... <file_name> - downloads one or more files\n")
    print("help - prints verbose for functions\n")
    print("quit - exits client interface\n")

def send_message(target_socket, metadata, message):
    """
    Send a message to a target socket with meta data
    """
    header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
    metadata = f"{metadata:<{META_LENGTH}}".encode('utf-8')
    message = message.encode('utf-8')
    target_socket.send(header + metadata + message)

def update_server():
    """
    send updated directory to server
    """
    try:
        list_of_dir = os.listdir(f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/")
        list_of_dir = '\n'.join(list_of_dir)
        send_message(strong_peer_socket, str(WEAK_PEER_ID) ,f"update_list {list_of_dir}")
    except:
        # client closed connection, violently or by user
        return False

def folder_watch_daemon():
    """
    A daemon that updates the directory to the server whenever a new file is added or an file is deleted
    """
    update_server()
    current_file_directory = os.listdir(f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/")

    while True:
        temp = os.listdir(f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/")
        if current_file_directory != temp:
            update_server()
            current_file_directory = temp

def wait_for_result(listening_socket):
    # Keep trying to recieve until client recieved returns from the server
    while True:
        try:
            # Receive our "header" containing username length, it's size is defined and constant
            header = listening_socket.recv(HEADER_LENGTH)

            # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
            if not len(header):
                log_this(f"Connection closed by the server")
                return

            # Convert header to int value
            header = int(header.decode('utf-8').strip())

            # Get meta data
            meta = listening_socket.recv(META_LENGTH)
            meta = meta.decode('utf-8').strip()

            # Receive and decode msg
            data = listening_socket.recv(header).decode('utf-8')

            # Break out of the loop when list is recieved                
            break

        except IOError as e:
            # Any other exception - something happened, exit
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                log_this('Reading error: {}'.format(str(e)))
                return

            # We just did not receive anything
            continue

        except Exception as e:
            # Any other exception - something happened, exit
            log_this('Reading error: '.format(str(e)))
            return

    return {"meta":meta, "data":data}

#################################################################HELPER FUNCTIONS###################################################################


###################################################################CLIENT RELATED###################################################################

def wait_for_list(full_command):
    """
    Waiting for a list of directories from the server
    """
    start = time.time()

    send_message(strong_peer_socket, '', full_command)
    log_this(f"Weak peer sent command to Strong Peer: {full_command}")
    
    result = wait_for_result(strong_peer_socket)

    dir_list = json.loads(result["data"])

    # Print List
    for client in dir_list:
        print(f"Weak Peer with id {client}:")
        for file in dir_list[client]:
            print(f"\t{file}")

def parallelize_wait_for_file_download(peer_socket, files):
    """
    waiting function for parallelized/serial file download
    """

    # Encode command to bytes, prepare header and convert to bytes, like for username above, then send
    send_message(peer_socket,'',f"download {' '.join(files)}")
    log_this(f"Client sent command: {full_command}")

    # open files
    fds = [open(f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/{files[i]}",'w') for i in range(len(files))]
    files_closed = 0
    redownload_count = 0

    # list of md5 hash for checksum reconstruction
    m = [hashlib.md5() for _ in range(len(files))]

    # Keep trying to recieve until client recieved returns from the server
    while True:
        try:
            start = time.time()

            # Get the header
            header = peer_socket.recv(HEADER_LENGTH)  

            # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
            if not len(header):
                log_this('Connection closed by the server')
                return
            
            # Convert header to int value
            header = int(header.decode('utf-8').strip())

            # Get meta data/ There should be a state and a client id 
            meta = peer_socket.recv(META_LENGTH)
            meta = meta.decode('utf-8').strip()
            meta = meta.split(' ')

            # Recieve line and convert to string
            line = peer_socket.recv(header).decode('utf-8') 

            # if there is any error, remove all files
            if meta[0] == 'ERROR':
                log_this(line)
                
                for i in range(len(files)):
                    fds[i].flush()
                    fds[i].close()
                    os.remove(f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/{files[i]}")
                break
            
            # Flush and close and files is finished recieving
            elif meta[0] == 'END':
                fds[int(meta[1])].flush()
                fds[int(meta[1])].close()
                files_closed += 1

                # If there is contamination in the checksum, log and delete file
                if m[int(meta[1])].hexdigest() != line:
                    log_this(f"Incorrect checksum for file : {files[int(meta[1])]}")
                    log_this(f"Deleting file : {files[int(meta[1])]}")
                    os.remove(f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/{files[int(meta[1])]}")
 
            # continue to write and flush to files
            else:
                m[int(meta[0])].update(line.encode('utf-8'))
                fds[int(meta[0])].write(line)
                fds[int(meta[0])].flush()
            
            # when all files are closed/downloaded sucessfully then we can break from the loop
            if files_closed == len(fds):
                end = time.time()
                log_this(f"DownloadComplete: {(end-start)*1000} ms. Downloaded Files are {' '.join(files)}")
                break

        except IOError as e:
            # Any other exception - something happened, exit
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                if redownload_count < REDOWNLOAD_TIME:
                    redownload_count += 1
                    continue
                
                log_this('Reading error: {}'.format(str(e)))
                return 

            # We just did not receive anything
            continue

        except Exception as e:
            # Any other exception - something happened, exit
            log_this('Reading error: {}'.format(str(e)))
            return

def wait_for_file_download(full_command,target_client, my_username):
    """
    Waiting for the file contents from the server    
    """
    parameters = full_command.split(' ')[1:]

    # if the target client is itself, don't do anything
    if target_client == WEAK_PEER_ID:
        log_this("WrongClient: Target Client is Current Client.")
        return

    # initialize connections with the other peer
    weak_peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    weak_peer_socket.connect((WEAK_PEERS[target_client]["ip_address"], WEAK_PEERS[target_client]["port"]))
    weak_peer_socket.setblocking(False)
    send_message(weak_peer_socket,'',my_username)

    # starts waiting for file download
    t = Thread(target=parallelize_wait_for_file_download, args=(weak_peer_socket, parameters,))
    t.start()

    return

def find_target(file1):
    """
    Ask strong peer to find a target
    """

    # Encode command to bytes, prepare header and convert to bytes, like for username above, then send
    send_message(strong_peer_socket,'',f"find_target {file1}")
    log_this(f"Client sent command: find_target")

    result = wait_for_result(strong_peer_socket)

    return int(result["data"])


###################################################################CLIENT RELATED###################################################################


###################################################################SERVER RELATED###################################################################
def receive_command(peer_socket):
    """
    Handles command receiving
    """
    try:
        # Receive our "header" containing command length, it's size is defined and constant
        command_header = peer_socket.recv(HEADER_LENGTH)

        # If we received no data, client gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
        if not len(command_header):
            return False
        
        # Convert header to int value
        command_length = int(command_header.decode('utf-8').strip())

        # Get meta data
        meta = peer_socket.recv(META_LENGTH)
        meta = meta.decode('utf-8').strip()

        # Get data 
        data = peer_socket.recv(command_length)
        data = data.decode('utf-8')

        # Return an object of command header and command data
        return {'header': command_header, 'meta': meta, 'data': data}

    except:
        # client closed connection, violently or by user
        return False

def send_files(peer_socket, peers, files):
    """
    Sends file to the peer
    """
    try:
        fds = [open(f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/{files[i]}",'r') for i in range(len(files))]
        
        for i in range(len(files)):
            # using md5 checksum
            m = hashlib.md5()
            
            while True:

                # read line
                line = fds[i].readline()

                if not line:
                    send_message(peer_socket,f'END {i}',m.hexdigest())
                    log_this(f"{files[i]} was sent to {peers[peer_socket]['data']}")
                    break
                
                line = line.encode('utf-8')

                # update md5 checksum
                m.update(line)

                # sending each line to target peer socket
                send_message(peer_socket, f'{i}', line)
            fds[i].close()

    except Exception as e:
        # client closed connection, violently or by user
        send_message(peer_socket, "ERROR", str(e))
        return False

def server_daemon():
    """
    A daemon that listens for download requests from any other weak peers 
    """

    # Create a server socket
    weak_peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    weak_peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    weak_peer_socket.bind((IP,SERVER_PORT))
    weak_peer_socket.listen()

    # Create list of sockets for select.select()
    sockets_list = [weak_peer_socket]

    # List of connected clients - socket as a key, user header and name as data
    peers = {}

    log_this(f'Listening for connections on {IP}:{SERVER_PORT}...')
    
    while True:
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        for notified_socket in read_sockets:
            
            # If notified socket is a server socket - new connection, accept it
            if notified_socket == weak_peer_socket:
                
                peer_socket, client_address = weak_peer_socket.accept()

                # Client should send his name right away, receive it
                user = receive_command(peer_socket)

                # If False - client disconnected before he sent his name 
                if user is False:
                    continue

                # Add accepted socket to select.select() list
                sockets_list.append(peer_socket)
                
                # Also save username and username header
                peers[peer_socket] = user

                #logging
                log_msg = 'Accepted new connection from {}:{}, username: {}'.format(*client_address, user['data'])
                log_this(log_msg)

            # Else existing socket is sending a command
            else:

                # Recieve command
                command = receive_command(notified_socket)

                # If False, client disconnected, cleanup
                if command is False:
                    log_msg = 'Closed connection from: {}'.format(peers[notified_socket]['data'])
                    log_this(log_msg)

                    # remove connections
                    sockets_list.remove(notified_socket)
                    del peers[notified_socket]
                    continue
                
                # Get user by notified socket, so we will know who sent the command
                user = peers[notified_socket]

                # Get command
                command_msg = command["data"].split(' ')

                # Get metadata
                command_meta = command["meta"]

                # logging
                log_msg = f'Recieved command from {user["data"]}: {command_msg[0]}\n'
                log_this(log_msg)

                # Handle commands
                if command_msg[0] == 'download':
                    start_new_thread(send_files, (notified_socket,peers,command_msg[1:],))
                    log_this(f"Start Downloading Files: {command_msg[1:]}")

            # handle some socket exceptions just in case
            for notified_socket in exception_sockets:
                
                # remove connections
                sockets_list.remove(notified_socket)
                del peers[notified_socket]

###################################################################SERVER RELATED###################################################################

if __name__ == "__main__":
    # Start the peer's server daemon
    start_new_thread(server_daemon,())
    time.sleep(3)

    # Initialize connection with the strong peer
    for edge in EDGES:
        node_1 = [edge[0][0],int(edge[0][1:])]
        node_2 = [edge[1][0],int(edge[1][1:])]
        
        if node_1[0] == "w" and node_2[0] == "s":
            if node_1[1] == WEAK_PEER_ID:
                strong_peer_ip = STRONG_PEERS[node_2[1]]['ip_address']
                strong_peer_port = STRONG_PEERS[node_2[1]]['port']
        
        if node_1[0] == "s" and node_2[0] == "w":
            if node_2[1] == WEAK_PEER_ID:
                strong_peer_ip = STRONG_PEERS[node_2[1]]['ip_address']
                strong_peer_port = STRONG_PEERS[node_1[1]]['port']
            
     
    strong_peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    strong_peer_socket.connect((strong_peer_ip, strong_peer_port))
    strong_peer_socket.setblocking(False)
    
    if len(sys.argv) == 1:
        # Manual Mode of Client Interface

        # create username to connect to the server
        my_username = f"weak_peer_{WEAK_PEER_ID}"
        send_message(strong_peer_socket,'WEAK',my_username)

        # Start folder watch daemon to automatically update to server
        start_new_thread(folder_watch_daemon,())
        
        # Print verbose client shell begins
        help()

        # Does Client Things
        while True:

            # Wait for user to input a command
            full_command = input(f'{my_username} > ').strip()
            command = full_command.split(' ')[0]
            parameters = full_command.split(' ')[1:]

            if command == "download":
                if len(parameters) != 0:
                    target_client = find_target(parameters[0])
                    wait_for_file_download(full_command,target_client,my_username)
                else:
                    log_this("ParameterError: Too less parameters")

            elif command == "get_files_list":
                if len(parameters) == 0:
                    wait_for_list(full_command)
                else:
                    log_this("ParameterError: Too many parameters")

            elif command == "help":
                help()
            
            elif command == "quit":
                send_message(strong_peer_socket,str(WEAK_PEER_ID),"unregister")
                log_this(f"Client sent command: {full_command}")
                LOG.close()
                sys.exit()
    
    else:
        # Automatic Mode of Client Interface

        #Args
        #python client.py command1 command2 ... commandn

        # create username to connect to the server
        my_username = f"weak_peer_{WEAK_PEER_ID}"
        send_message(strong_peer_socket,'WEAK',my_username)

        # Start folder watch daemon to automatically update to server
        start_new_thread(folder_watch_daemon,())
        time.sleep(3)
        
        # Does Client Things
        for i in sys.argv[1:]:

            # give time to process command
            time.sleep(1)

            # Wait for user to input a command
            full_command = i
            command = full_command.split(' ')[0]
            parameters = full_command.split(' ')[1:]

            if command == "download":
                if len(parameters) != 0:
                    wait_for_file_download(full_command,my_username)
                else:
                    log_this("ParameterError: Too less parameters")

            elif command == "get_files_list":
                if len(parameters) == 0:
                    wait_for_list(full_command)
                else:
                    log_this("ParameterError: Too many parameters")

            elif command == "help":
                help()
            
            elif command == "quit":
                send_message(strong_peer_socket,str(WEAK_PEER_ID),"unregister")
                log_this(f"Client sent command: {full_command}")
                LOG.close()
                sys.exit()