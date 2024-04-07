import grpc
from concurrent import futures
import time
import replication_pb2
import replication_pb2_grpc
import heartbeat_service_pb2
import heartbeat_service_pb2_grpc
import redis 
from redis.cluster import RedisCluster
import threading

# connecting to redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
hash_key = 'info_backup:321' # defining name of dictionary entry in redis

class SequenceServicer(replication_pb2_grpc.SequenceServicer):
    
    # function to write - called by primary
    def Write(self, request, context):
        key = request.key
        value = request.value

        # write in backup database
        r.hset(hash_key, key, value)

        # update log
        with open("backup.txt", 'a') as file: # 'a' so we can append if it already exists
            file.write(key + ":" + value + "\n")

        return replication_pb2.WriteResponse(ack="done")
    
    def __init__(self): # so it can work in the background and the backup can still receive requests from clients (primary)
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True) # start thread to send hearbeats to heartbeat server
        heartbeat_thread.start()
    
    def send_heartbeat(self): # function to send hearbeat to server every 5 seconds
        with grpc.insecure_channel('localhost:50053') as channel: # connect to heartbeat server
            stub = heartbeat_service_pb2_grpc.ViewServiceStub(channel)
            while True:
                try:
                    # send the heartbeat
                    stub.Heartbeat(heartbeat_service_pb2.HeartbeatRequest(service_identifier="Backup"))
                except:
                    print(f"Failed to send heartbeat.")

                # wait 5 sec between heartbeats
                time.sleep(5)
    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    replication_pb2_grpc.add_SequenceServicer_to_server(SequenceServicer(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

