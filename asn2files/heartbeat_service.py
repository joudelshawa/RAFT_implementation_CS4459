import grpc
from concurrent import futures
import time
import heartbeat_service_pb2
import heartbeat_service_pb2_grpc
import threading
from google.protobuf import empty_pb2

class ViewServiceServicer(heartbeat_service_pb2_grpc.ViewServiceServicer):
    
    # dictionary to keep track of latest heartbeats received by each server
    last_heartbeat = {}

    # function to log heartbeat (called by servers)
    def Heartbeat(self, request, context):
        id = request.service_identifier
        self.last_heartbeat[id] = time.time() # log timestamp of heartbeat for the id received

        with open("heartbeat.txt", "a") as file: # update that alive in logs only when we get a heartbeat
            file.write(f"{id} is alive. Latest heartbeat received at {time.ctime(self.last_heartbeat[id])}\n")
            
        return empty_pb2.Empty()

    # local func when we initialize the server so it can start checking and updating the log files
    def __init__(self): # so it can work in the background and still receive requests from clients
        heartbeat_thread = threading.Thread(target=self.check_heartbeat, daemon=True)
        heartbeat_thread.start()
    
    def check_heartbeat(self):
        while True: # do constantly

            current_time = time.time()

            for id, last_time in list(self.last_heartbeat.items()):

                if current_time - last_time > 5:

                    # if more than 5 sec passed, log that the server might be down
                    with open("heartbeat.txt", "a") as file:
                        file.write(f"{id} might be down. Latest heartbeat received at {time.ctime(last_time)}\n")
                    
                    # remove from tracking to avoid repeated logs
                    del self.last_heartbeat[id]

            time.sleep(1) # lag to make sure things are up to date

    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    heartbeat_service_pb2_grpc.add_ViewServiceServicer_to_server(ViewServiceServicer(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

