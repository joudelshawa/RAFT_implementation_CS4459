import grpc
import raft_pb2
import raft_pb2_grpc

if __name__ == '__main__':

    done = False
    while not done:

        print("---------------------------------") # separator
    
        # get user input 
        user_input = input("press 'q' to quit or enter 'e' to edit servers or any other key to edit: ")

        if user_input.lower() == "q": # if q, then quit 
            done = True
        elif user_input.lower() == "e": # if e, then edit servers 
            done = True