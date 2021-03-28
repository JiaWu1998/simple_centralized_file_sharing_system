import socket
import select
import os
import datetime
from _thread import *
import json
from pathlib import Path
import hashlib
from collections import defaultdict
import random
import sys

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

global_file_list = json_peer_files

strong_peer_graph = None
neighbor_strong_peer_sockets = {}

query_id = None

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

class Graph:
    """
    A Graph class for super peers
    """
    def __init__(self,vertices):
        self.V = vertices 
        self.V_org = vertices
        self.graph = defaultdict(list) 
        self.shortest_path = []
   
    def addEdge(self,u,v,w):
        if w == 1:
            self.graph[u].append(v)
        else:    
            self.graph[u].append(self.V)
            self.graph[self.V].append(v)
            self.V = self.V + 1

    def printPath(self, parent, j):
        if parent[j] == -1 and j < self.V_org :
            self.shortest_path.append(j)
            return self.shortest_path
        self.printPath(parent , parent[j])
        if j < self.V_org :
            self.shortest_path.append(j)
        return self.shortest_path

    def findShortestPath(self,src, dest):
        visited =[False]*(self.V)
        parent =[-1]*(self.V)
        queue=[]
        queue.append(src)
        visited[src] = True
        while queue :
            s = queue.pop(0)
            if s == dest:
                return self.printPath(parent, s)
            for i in self.graph[s]:
                if visited[i] == False:
                    queue.append(i)
                    visited[i] = True
                    parent[i] = s

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

def passing_message(target, message):
    """
    passes message to the next node in the path to the target
    """
    shortest_path = strong_peer_graph.findShortestPath(STRONG_PEER_ID,target)
    next_node = shortest_path[1]

    send_message(neighbor_strong_peer_sockets[next_node],'', message)

def update_global_file_directory():
    """
    Broadcast query to all strong peers
    """
    
    query_id = random.randint(0,sys.maxsize)

    for i in range(len(STRONG_PEERS)):
        if i != STRONG_PEER_ID:
            passing_message(i, f"QUERY_ID:{query_id} FROM:{STRONG_PEER_ID} TO:{i} DATA:file_list") 

    # WAIT FOR ARRIVE and update global file list


def send_file_directory(client_socket, target_type):
    """
    Sends file directory to client by id or passes a message to another peer
    """
    try:
        if target_type == "WEAK":
            send_message(client_socket, "", json.dumps(global_file_list))
        elif target_type == "STRONG":
            send_message(client_socket, "", f"QUERY_ID:{query_id} FROM:{STRONG_PEER_ID} TO:{i} DATA:{json.dumps(json_peer_files)}")
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
    # Initialize super peer graph
    strong_peer_graph = Graph(len(STRONG_PEERS))
    for i in range(len(EDGES)):
        if EDGES[i][0][0] == "s" and EDGES[i][1][0] == "s":
            strong_peer_graph.addEdge(int(EDGES[i][0][1]),int(EDGES[i][1][1]),1)

    #Initialize connections with other NEIGHBOR super peers
    for edge in EDGES:
        node_1 = [edge[0][0],int(edge[0][1])]
        node_2 = [edge[1][0],int(edge[1][1])]

        if node_1[0] == "s" and node_2[0] == "s":
            if node_1[1] == STRONG_PEER_ID or node_2[1] == STRONG_PEER_ID:
                temp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                strong_peer_port =  STRONG_PEERS[node_2[1]]['port'] if node_1[1] == STRONG_PEER_ID else STRONG_PEERS[node_1[1]]['port']
                temp_connection.connect((IP,strong_peer_port))
                temp_connection.setblocking(False)
                send_message(temp_connection, 'STRONG', f"strong_peer_{STRONG_PEER_ID}")
                other_strong_peer_id =  node_2[1] if node_1[1] == STRONG_PEER_ID else node_1[1]
                neighbor_strong_peer_sockets[other_strong_peer_id] = temp_connection
    
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
                    
                    # if the query have hit the target
                    if command_msg[3] == f"TO:{STRONG_PEER_ID}":
                        pass

                    # if not, keep passing_message
                    else:
                        start_new_thread(passing_message,(int(command_msg[3].split(':')[1]),command["data"],))

        # handle some socket exceptions just in case
        for notified_socket in exception_sockets:
            
            # remove connections
            sockets_list.remove(notified_socket)
            del clients[notified_socket]