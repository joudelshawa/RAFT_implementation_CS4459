import grpc
from concurrent import futures
import time
import raft_pb2
import raft_pb2_grpc
import redis 
from redis.cluster import RedisCluster
import threading
from server import RAFTServiceServicer
import os

class Manager:

    def __init__(self) -> None:
        self.servers = {}
        self.leader = None
        self.id_count = 0
        self.channel_index = 50050
        self.dirpath = "./logs"

        # make dir for log files
        try:
            os.makedirs(self.dirpath)
            print(f"Directory was created successfully.")
        except FileExistsError:
            print(f"Directory already exists.")

    def serve(self, id, channel, peers, path):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        raft_pb2_grpc.add_RAFTServiceServicer_to_server(RAFTServiceServicer(id, channel, peers, path), server)
        port = "[::]:" + str(channel)
        server.add_insecure_port(port)
        server.start()
        server.wait_for_termination()

    def addServer(self):
        self.id_count += 1
        self.channel_index += 1
        path = self.dirpath + "/logs_" + str(self.id_count) + ".txt"
        
        # now start the server
        self.serve(self.id_count, self.channel_index, self.servers, path)

        # add channel to dict
        self.servers[self.id_count] = self.channel_index


   

