import threading
import random
import time
import grpc
from concurrent import futures
import raft_pb2
import raft_pb2_grpc
import redis 
from redis.cluster import RedisCluster
import threading

class RAFTServiceServicer(raft_pb2_grpc.RAFTServiceServicer):

    def __init__(self, id, channel, peers, folder_path):
        
        # init main components
        self.id = id
        self.channel = channel
        self.peers = peers
        self.folder_path = folder_path
        self.state = "follower" # could be a "leader" or "candidate" for elections
        
        # for checking if previous log matches
        self.lastIndex = -1
        self.lastTerm = -1

        # for checking current term
        self.term = 0

        # init log
        with open(self.folder_path, 'a') as file: # 'a' so we can append if it already exists
            file.write(f"server {id} online. format is 'id:term#'")

    def AppendEntries(self, request, context):
        term = request.term
        leaderId = request.leaderId # don't think we need?
        previousLogIndex = request.prevLogIndex
        previousLogTerm = request.prevLogTerm
        leaderIndex = request.leaderCommit

        if (self.lastIndex == previousLogIndex and self.lastTerm == previousLogTerm): # if they match then you can add the new log
            with open(self.folder_path, 'a') as file: # 'a' so we can append if it already exists
                file.write(f"{leaderIndex}:{term}") # layout is index:term
            self.lastIndex = leaderIndex
            self.lastTerm = term
            self.term = term

            return raft_pb2.AppendEntriesResponse(term = self.term, success = True)

        else:
            return raft_pb2.AppendEntriesResponse(term = self.term, success = False)

    def ReconcileLogs(self, request, context):
        path = request.filepath

        try:
            with open(path, 'r') as file1, open(self.folder_path, 'r') as file2:
                
                # read all lines from each log file
                leader_lines = file1.readlines()
                follower_lines = file2.readlines()

                changed = False # bool to track if we need to change follower file
                
                # skip the first line and have the same number of logs in both files
                for i in range(1, len(leader_lines)):
                    if i < len(follower_lines):
                        if leader_lines[i] != follower_lines[i]: # if lines are not the same
                            print(f"Correcting difference:\nOriginal in follower: {follower_lines[i]}New in follower: {leader_lines[i]}")
                            follower_lines[i] = leader_lines[i]  # sync up lines from leader file
                            changed = True
                    else:
                        # leader has more logs than follower, append these lines to follower
                        print(f"Appending missing line from leader to follower: {leader_lines[i]}")
                        follower_lines.append(leader_lines[i])
                        changed = True

            # write the updated lines back to follower - TODO note that you still need to call the appendentries function again for any uncommitted data!!
            if changed:
                with open(self.filepath, 'w') as file2:
                    file2.writelines(follower_lines)
            
            return raft_pb2.ReconcileResponse(success = True)

        except: 
            print("something went wrong!")
            return raft_pb2.ReconcileResponse(success = False)


    def RequestVote(self, request, context):
        pass










    # use following LATER
        # self.electionTimeout = random.uniform(150, 300)  # random timeout based on slides
    
