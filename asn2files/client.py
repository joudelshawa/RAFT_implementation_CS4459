import grpc
import replication_pb2
import replication_pb2_grpc

if __name__ == '__main__':

    done = False
    while not done:

        print("---------------------------------") # separator

        # get user input 
        user_input = input("press 'q' to quit or enter a key to edit: ")

        if user_input.lower() == "q": # if q, then quit 
             done = True
        else: # otherwise, they just input a key so send it to the primary server
            key = user_input
            value = input("edit value: ")
            try:
                with grpc.insecure_channel('localhost:50051') as channel:
                    stub = replication_pb2_grpc.SequenceStub(channel)
                    response = stub.Write(replication_pb2.WriteRequest(key=key, value=value))
                    print(response.ack)

                    # update log
                    with open("client.txt", 'a') as file: # 'a' so we can append if it already exists
                        file.write(key + ":" + value + "\n")
            except:
                print("something went wrong!")


