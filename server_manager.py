from servicer import RAFTServiceServicer
import threading
from collections import defaultdict
import grpc
from concurrent import futures
import time
import raft_pb2
import raft_pb2_grpc
import os
import glob


# ServerManager class definition
class ServerManager:
    def __init__(self):
        self.servers = {}
        self.channels = {}
        self.server_threads = {}

    def start_server(self, server_id, port):
        if server_id not in self.servers:
            isPrimary = False
            filtered_channels = {k: v for k, v in self.channels.items() if k != server_id} # filter out itself from channels
            if len(self.servers) == 0: 
                isPrimary = True # only make the very first server activated the primary server
                server = RAFTServiceServicer(server_id, port, filtered_channels, isPrimary, server_id)
            else:
                server = RAFTServiceServicer(server_id, port, filtered_channels, isPrimary, self.get_Primary())
            
            # add new server to list
            self.channels[server_id] = grpc.insecure_channel(f"localhost:{port}")
            thread = threading.Thread(target=server.serve, daemon=True)
            self.servers[server_id] = server
            self.server_threads[server_id] = thread
            thread.start()
            print(f"{server_id} started on port {port}.")
            
            # update other servers to tell them new one has joined
            for id in self.servers.keys():
                if server_id != id: # dont add yourself to the list
                    print(f"server id: {id} adding new server {server_id}")
                    self.servers[id].addSecondary(server_id, port)

        else:
            print(f"{server_id} is already running.")

    def stop_server(self, server_id):
        if server_id in self.servers:
            self.servers[server_id].stop()  # stop server
            self.server_threads[server_id].join()  # join the thread after the server has stopped
            del self.servers[server_id]
            del self.channels[server_id]
            del self.server_threads[server_id]
            print(f"{server_id} has been stopped.")

            # remove from other servers
            for id in self.servers.keys():
                self.servers[id].removeSecondary(server_id)

        else:
            print(f"{server_id} is not running.")
    
    def get_Primary(self):
        diff_leaders = defaultdict(int)  # dict to keep track of how many times each id is said, taking majority as primary (in case different servers think different things)
        for server_id in self.servers.keys():
            leader = self.servers[server_id].getPrimary() 
            diff_leaders[leader] += 1

        # get leader with the majority
        majority_leader = None
        max_count = 0
        for leader, count in diff_leaders.items():
            if count > max_count:
                max_count = count
                majority_leader = leader

        print(f"The majority leader is {majority_leader} with {max_count} votes.")
        return majority_leader

    def stop_all_servers(self):
        for server_id in list(self.servers.keys()):
            self.stop_server(server_id)


def delete_files(pattern): # function to delete old output files (from previous run) since we dont want to confuse user
    files = glob.glob(pattern) # match files based on pattern
    for file in files:
        try:
            os.remove(file)
        except Exception as e:
            print(f"failed to delete {file}: {str(e)}")

# Main function to run the ServerManager
def main():
    delete_files('heartbeat_*.txt')
    delete_files('log_*.txt')
    delete_files('output_*.txt')
    print(f"deleted old files")

    manager = ServerManager()
    user_input = input("what would you like to do? eg. 'start server1', 'input 1 12', etc. enter q to quit\n")
    while (user_input != "q"):
        user_input = user_input.lower().strip() # make lowercase and remove any whitespace

        if user_input.startswith("start") or user_input.startswith("add"):
            id = user_input.split("erver")[1].strip()
            manager.start_server(f'Server {id}', 50050+int(id))
        
        if user_input.startswith("stop") or user_input.startswith("end"):
            if (user_input.endswith("all")):
                manager.stop_all_servers()
            else:
                manager.stop_server(f'Server {user_input.split("erver")[1].strip()}')
        
        if user_input.startswith("input"):
            if len(manager.servers) > 0:
                leader = manager.get_Primary()
                chan = 50050+int(leader.split("erver")[1].strip())

                try:
                    with grpc.insecure_channel(f'localhost:{chan}') as channel:
                        inputs = user_input.split(" ")
                        stub = raft_pb2_grpc.RAFTServiceStub(channel)
                        response = stub.Write(raft_pb2.WriteRequest(key=inputs[1], value=inputs[2]))
                        print(response.ack)

                        # update log
                        with open("client.txt", 'a') as file: # 'a' so we can append if it already exists
                            file.write(inputs[1] + ":" + inputs[2] + "\n")
                except:
                    print("something went wrong!")
            else:
                print("no servers active!")

        user_input = input("what would you like to do? eg. 'start server1', etc. enter q to quit\n")
    
    # if user input q, just end program
    manager.stop_all_servers()


if __name__ == '__main__':
    main()