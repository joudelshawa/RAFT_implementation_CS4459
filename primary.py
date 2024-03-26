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
hash_key = 'info:123' # defining name of dictionary entry in redis

class SequenceServicer(replication_pb2_grpc.SequenceServicer):
    
    # function to write (called by clients)
    def Write(self, request, context):
        key = request.key
        value = request.value

        with grpc.insecure_channel('localhost:50052') as channel: # connect to backup

            # write in backup first
            stub = replication_pb2_grpc.SequenceStub(channel)
            response = stub.Write(replication_pb2.WriteRequest(key=key, value=value))

            if response.ack == "done": # if backup response is all good and its done writing
                
                # write in primary
                r.hset(hash_key, key, value)

                # update log
                with open("primary.txt", 'a') as file: # 'a' so we can append if it already exists
                    file.write(key + ":" + value + "\n")
                    
                return replication_pb2.WriteResponse(ack="done")
            
            else: # something went wrong with backup - didnt do try-except because was told its out of scope of the assignment
                context.set_code(grpc.StatusCode.UNKNOWN)
                return
            
    def __init__(self): # so it can work in the background and the primary can still receive requests from clients
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
    
    # function to send heartbeats in the background to the heartbeat server
    def send_heartbeat(self):
        with grpc.insecure_channel('localhost:50053') as channel: # connect to heartbeat server
            stub = heartbeat_service_pb2_grpc.ViewServiceStub(channel)
            while True:
                try:
                    # send the heartbeat
                    stub.Heartbeat(heartbeat_service_pb2.HeartbeatRequest(service_identifier="Primary"))
                except:
                    print(f"Failed to send heartbeat.")

                # wait 5 sec between heartbeats
                time.sleep(5)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    replication_pb2_grpc.add_SequenceServicer_to_server(SequenceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

