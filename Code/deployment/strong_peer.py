import socket
import select
import os
import datetime
from _thread import *
import json
from pathlib import Path
import hashlib

# get configurations
config = json.load(open(f"{os.path.dirname(os.path.abspath(__file__))}/config.json"))

EDGES = config['edges']
STRONG_PEERS = config['strong_peers']
WEAK_PEERS = config['weak_peers']

STRONG_PEER_ID = int(os.path.basename(Path(os.path.realpath(__file__)).parent).split('_')[1])
IP = STRONG_PEERS[STRONG_PEER_ID]['ip_address']
SERVER_PORT = STRONG_PEERS[STRONG_PEER_ID]['port']
HOST_FOLDER = STRONG_PEERS[STRONG_PEER_ID]['host_folder']
HEADER_LENGTH = config['header_length']
META_LENGTH = config['meta_length']
LOG = open(f"{os.path.dirname(os.path.abspath(__file__))}/{config['server']['log_file']}", "a")

LOCAL_LIBRARY_DIR = f"{os.path.dirname(os.path.abspath(__file__))}/{HOST_FOLDER}/client_files.json"
LOCAL_WEAK_PEER_FILES = open(LOCAL_LIBRARY_DIR, "w+")
json_peer_files = json.load(LOCAL_WEAK_PEER_FILES) if os.stat(LOCAL_LIBRARY_DIR).st_size != 0 else json.loads(json.dumps({}))

#################################################################HELPER FUNCTIONS###################################################################

def log_this(msg):
    """
    Logs a message
    """
    print(msg)
    LOG.write(f"{datetime.datetime.now()} {msg}\n")
    LOG.flush()

def send_message(target_socket, metadata, message):
    """
    Send a message to a target socket with meta data
    """
    header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
    metadata = f"{metadata:<{META_LENGTH}}".encode('utf-8')
    message = message.encode('utf-8')
    target_socket.send(header + metadata + message)

def find(parent, i):
    """
    A utility function to find set of an element i. It uses path compression.
    """
    if parent[i] == i:
        return i
    return find(parent, parent[i])

def union(parent, rank, x, y):
    """
    A function that does union of two sets of x and y. uses union by rank
    """
    xroot = find(parent, x)
    yroot = find(parent, y)

    if rank[xroot] < rank[yroot]:
        parent[xroot] = yroot
    elif rank[xroot] > rank[yroot]:
        parent[yroot] = xroot
    else:
        parent[yroot] = xroot

def create_span_tree():
    """
    Creates minimum spannning tree with kruskals minimum spanning tree algorithm
    """
    spanning_tree = []

    # Creates the super peer graph
    super_peer_graph = []

    for i in range(len(EDGES)):
        if EDGES[i][0][0] == "s" and EDGES[i][1][0] == "s":
            super_peer_graph.append([int(EDGES[i][0][1]),int(EDGES[i][1][1]), i])
    
    # index variable for sorted edges
    i = 0

    # index variable for spanning tree array
    e = 0

    parent = []
    rank = []

    for node in range(len(STRONG_PEERS)):
        parent.append(node)
        rank.append(0)
    
    while e < len(STRONG_PEERS) - 1:
        u, v, w  = super_peer_graph[i]
        i += 1
        x = find(parent, u)
        y = find(parent, v)

        if x != y:
            e = e + 1
            spanning_tree.append([u,v,w])
            union(parent, rank, x, y)
    
    return spanning_tree

#################################################################HELPER FUNCTIONS###################################################################

###################################################################SERVER RELATED###################################################################
def receive_command(client_socket):
    """
    Handles command receiving
    """
    try:
        # Receive our "header" containing command length, it's size is defined and constant
        command_header = client_socket.recv(HEADER_LENGTH)

        # If we received no data, client gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
        if not len(command_header):
            return False

        # Convert header to int value
        command_length = int(command_header.decode('utf-8').strip())

        # Get meta data
        meta = client_socket.recv(META_LENGTH)
        meta = meta.decode('utf-8').strip()

        # Get data
        data = client_socket.recv(command_length)
        data = data.decode('utf-8')

        # Return an object of command header and command data
        return {'header': command_header, 'meta': meta, 'data': data}

    except:
        # client closed connection, violently or by user
        return False

def send_file_directory(weak_peer_id):
    """
    Sends file directory to client
    """
    try:
        send_message(weak_peer_id, "", json.dumps(json_peer_files))

    except:
        # client closed connection, violently or by user
        return False

def update_file_directory(weak_peer_id, dir_list):
    """
    Updates local weak peer library 
    """
    json_peer_files[weak_peer_id] = dir_list.split('\n')

    # clear file and rewrite
    LOCAL_WEAK_PEER_FILES.truncate(0)
    LOCAL_WEAK_PEER_FILES.write(f"{json.dumps(json_peer_files)}")
    LOCAL_WEAK_PEER_FILES.flush()

def unregister_client(weak_peer_id):
    """
    Unregister weak peer from library
    """
    del json_peer_files[weak_peer_id]

    # clear file and rewrite
    LOCAL_WEAK_PEER_FILES.truncate(0)
    LOCAL_WEAK_PEER_FILES.write(f"{json.dumps(json_peer_files)}")
    LOCAL_WEAK_PEER_FILES.flush()

###################################################################SERVER RELATED###################################################################

if __name__ == "__main__":
    #Initialize connections with other super peers
    other_strong_peers = []

    for edge in EDGES:
        node_1 = [edge[0][0],int(edge[0][1])]
        node_2 = [edge[1][0],int(edge[1][1])]

        if node_1[0] == "s" and node_2[0] == "s":
            if node_1[1] == STRONG_PEER_ID or node_2[1] == STRONG_PEER_ID:
                temp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                strong_peer_port =  STRONG_PEERS[node_2[1]]['port'] if node_1[1] == STRONG_PEER_ID else STRONG_PEERS[node_1[1]]['port']
                temp_connection.connect((IP,strong_peer_port))
                temp_connection.setblocking(False)
                other_strong_peers.append(temp_connection)
    
    # Create a server socket
    strong_peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    strong_peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    strong_peer_socket.bind((IP, SERVER_PORT))
    strong_peer_socket.listen()

    # Create list of sockets for select.select()
    sockets_list = [strong_peer_socket]

    # List of connected clients - socket as a key, user header and name as data
    clients = {}

    log_this(f'Listening for connections on {IP}:{SERVER_PORT}...')

    # Does Server Things
    while True:
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        for notified_socket in read_sockets:

            # If notified socket is a server socket - new connection, accept it
            if notified_socket == strong_peer_socket:

                client_socket, client_address = strong_peer_socket[strong_peer_socket.index(notified_socket)].accept()

                # Client should send his name right away, receive it
                user = receive_command(client_socket)

                # If False - client disconnected before he sent his name
                if user is False:
                    continue

                # Add accepted socket to select.select() list
                sockets_list.append(client_socket)

                # Also save username and username header
                clients[client_socket] = user

                # logging 
                log_msg = 'Accepted new connection from {}:{}, username: {}'.format(*client_address, user['data'].decode('utf-8'))
                log_this(log_msg)
            
            # Else existing socket is sending a command
            else:

                # Receive command
                command = receive_command(notified_socket)

                # If False, client disconnected, cleanup
                if command is False:
                    log_msg = '{} Closed connection from: {}'.format(datetime.datetime.now(), clients[notified_socket]['data'].decode('utf-8'))                 
                    log_this(log_msg)

                    # remove connections
                    sockets_list.remove(notified_socket)
                    del clients[notified_socket]
                    continue

                # Get user by notified socket, so we will know who sent the command
                user = clients[notified_socket]

                # Get command
                command_msg = command["data"].split(' ')
                
                # Get metadata
                command_meta = command["meta"]

                # logging
                log_msg = f'{datetime.datetime.now()} Received command from {user["data"].decode("utf-8")}: {command_msg[0]}'
                log_this(log_msg)

                # Handle commands from weak peers
                if user["meta"] == "WEAK":

                    if command_msg[0] == 'get_files_list':
                        start_new_thread(send_file_directory, (notified_socket,))
                        log_this(f'Sent file list to {user["data"].decode("utf-8")}')

                    elif command_msg[0] == 'update_list':
                        start_new_thread(update_file_directory, (int(command_meta),command_msg[1],))
                        log_this(f"Update directory for client_{int(command_meta)}")

                    elif command_msg[0] == 'unregister':
                        start_new_thread(unregister_client, (int(command_meta),))
                        log_this(f"Unregister client_{int(command_meta)}")

                if user["meta"] == "STRONG":
                    pass

        # handle some socket exceptions just in case
        for notified_socket in exception_sockets:
            
            # remove connections
            sockets_list.remove(notified_socket)
            del clients[notified_socket]