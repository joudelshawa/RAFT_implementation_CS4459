import grpc
from concurrent import futures
import time
import raft_pb2
import raft_pb2_grpc
import redis
from redis.cluster import RedisCluster
import threading
from google.protobuf import empty_pb2
import os
import random


class RAFTServiceServicer(raft_pb2_grpc.RAFTServiceServicer):

    # SETUP

    def __init__(self, id, channel, list_of_servers, isPrimary,
                 leader):  # so it can work in the background and the backup can still receive requests from clients (primary)
        self.id = id
        self.channel = channel
        self.server = None
        self.channels = list_of_servers

        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.hash_key = f'info_{self.id}'

        # files needed 
        self.log_file_path = f"./log_{id}.txt"
        self.write_file_path = f"./write_{id}.txt"
        self.heartbeat_file_path = f"./heartbeat_{id}.txt"
        self.output_file_path = f"./output_{id}.txt"

        self.leaderId = leader
        self.output(f"leader is {self.leaderId}")
        self.output(f"{id} primary {isPrimary}")
        self.isPrimary = isPrimary  # to indicate if server is the primary server
        self.isCandidate = False  # to indicate if server is currently performing an election
        self.voted = False  # to indicate if already voted during elections
        self.voted_for = ""  # to indicate which server they voted for in case of split-brain elections

        # timestamps to control for multiple elections going off at the same time
        # helps us manage back-to-back elections (not the same as the timeout - check report for more details!)
        self.primary_down_timestamp = 0
        self.primary_announcement_timestamp = 0

        # for appending entries and reconciling with primary
        self.lastIndex = -1
        self.lastIndexTerm = -1
        self.term = 1
        self.heartbeat_timer = 10

        # dictionary to keep track of latest heartbeats received by each server
        self.last_heartbeat = {}

        self.shutdown_event = threading.Event()  # event to signal thread shutdown when done

        self.setup_background_tasks()

    def setup_background_tasks(self):  # function to set up background tasks on init
        # start sending heartbeats
        self.send_heartbeat_thread = threading.Thread(
            target=self.send_heartbeat)  # start thread to send hearbeats to heartbeat server
        self.send_heartbeat_thread.start()

        # local func when we initialize the server so it can start checking and updating the log files
        # so it can work in the background and still receive requests from clients
        self.check_heartbeat_thread = threading.Thread(target=self.check_heartbeat)
        self.check_heartbeat_thread.start()

        # init log 
        with open(self.log_file_path,
                  'w') as file:  # 'w' so we can overwrite if it already exists (already lost that data)
            file.write(f"{self.id} online. format is 'index:term#'\n")

    # function to log what would have been in the terminal output
    def output(self, text):
        if os.path.exists(self.output_file_path) and os.path.getsize(
                self.output_file_path) > 0:  # if already exists add new line before saying server on
            text = "\n" + text
        with open(self.output_file_path, 'a') as file:  # 'a' so we can append if it already exists
            file.write(text)

    # function to return current primary
    def getPrimary(self):
        return self.leaderId

    # function to add new server to cluster
    def addSecondary(self, new_id, new_channel):
        self.channels[new_id] = grpc.insecure_channel(f"localhost:{new_channel}")
        self.output(f"added {new_id} to channels! so now theyre {self.channels.keys()}")

    # function to remove server from cluster if it goes down
    def removeSecondary(self, id):
        self.channels.pop(id, None)

    # GRPC functions

    # function to write - ONLY called if primary
    def Write(self, request, context):
        if self.shutdown_event.is_set():
            return
        success = []
        if self.isPrimary:  # if primary, tell create appendentries RPC
            if ((len(self.channels) + 1) < 3):  # if we dont have 3 or more servers, dont try to append anything
                return raft_pb2.WriteResponse(
                    ack=f"not enough servers active. currently have {(len(self.channels) + 1)} and need at least 3")

            self.output(f"primary, sending append entries request! to {self.channels.keys()}")
            for name, channel in list(self.channels.items()):  # connect to other servers
                # create stub with current channel so we can send appendentry rpc to server
                stub = raft_pb2_grpc.RAFTServiceStub(channel)
                try:
                    # send the appendentries request
                    response = stub.AppendEntries(
                        raft_pb2.AppendEntriesRequest(term=self.term, leaderId=self.id, prevLogIndex=self.lastIndex,
                                                      prevLogTerm=self.lastIndexTerm, leaderCommit=self.lastIndex + 1,
                                                      keyInput=request.key, valueInput=request.value))
                    if response.success:
                        success.append(1)
                        self.output(f"appended entries for {name}")
                    else:  # if its not successful, we need to reconcile entries
                        # try reconcile logs req
                        try:
                            response = stub.ReconcileLogs(
                                raft_pb2.ReconcileRequest(term=self.term, leaderId=self.id, prevLogIndex=self.lastIndex,
                                                          prevLogTerm=self.lastIndexTerm, filepath=self.log_file_path))
                            if response.success: self.output(f"reconciled entries for {name}!")
                            # send the appendentries request again for the new data
                            response = stub.AppendEntries(
                                raft_pb2.AppendEntriesRequest(term=self.term, leaderId=self.id,
                                                              prevLogIndex=self.lastIndex,
                                                              prevLogTerm=self.lastIndexTerm,
                                                              leaderCommit=(self.lastIndex + 1), keyInput=request.key,
                                                              valueInput=request.value))
                            if response.success:
                                success.append(1)
                                self.output(f"appended entries for {name}")
                            else:
                                self.output("something went wrong while appending after reconciliation.")
                        except Exception as e:
                            self.output(f"failed to send reconcilelogs to {name}.")
                except Exception as e:
                    self.output(f"failed to send appendentries to {name}.")

        self.output(f"sum: {sum(success)}")
        if sum(success) + 1 > (
                len(self.channels) + 1) / 2:  # if more than majority confirmed appendentries, actually append it
            # update write stuff
            key = request.key
            value = request.value

            # write in primary database
            self.redis.hset(self.hash_key, key, value)

            # update write log
            with open(self.write_file_path, 'a') as file:  # 'a' so we can append if it already exists
                file.write(key + ":" + value + "\n")

            # update log for future
            self.lastIndex += 1  # increase last index
            self.lastIndexTerm = self.term  # update term in case it wasnt right

            with open(self.log_file_path, 'a') as file:  # 'a' so we can append if it already exists
                file.write(f"index {self.lastIndex} : term {self.term}\n")

            # return confirmation for client
            return raft_pb2.WriteResponse(ack="done")
        else:
            # return error for client
            return raft_pb2.WriteResponse(ack="something went wrong. not enough servers confirmed.")

            # function to append entries - called by primary

    def AppendEntries(self, request, context):
        if self.shutdown_event.is_set():  # if shutting down dont do anything
            return raft_pb2.AppendEntriesResponse(success=False)

        term = request.term
        leaderId = request.leaderId
        previousLogIndex = request.prevLogIndex
        previousLogTerm = request.prevLogTerm
        leaderIndex = request.leaderCommit

        # if server is a candidate (has an active election) and receives an appendentries RPC from another 
        # that has a term >= to this one's, step down from election and continue
        if self.isCandidate and term >= self.term: self.isCandidate = False

        # check if this is just an empty appendentries request to announce new leader
        if leaderIndex == -1:
            self.output(f"received blank appendentries request for new leader {leaderId}")
            # log when you received primary announcement so we dont have back to back elections
            self.primary_announcement_timestamp = time.time()
            # update stuff to indicate new primary - dont change the last log index and term bc may need reconciling
            self.term = term
            self.leaderId = leaderId
            self.isPrimary = False
            self.voted = False  # reset vote boolean for next election
            self.output(f"***** updated primary to {self.leaderId}!")
            return raft_pb2.AppendEntriesResponse(term=self.term, success=True)

        # if previous index and term match then you can add the new log
        if (self.lastIndex == previousLogIndex and self.lastIndexTerm == previousLogTerm):
            with open(self.log_file_path, 'a') as file:  # 'a' so we can append if it already exists
                file.write(f"index {leaderIndex} : term {term}\n")  # layout is index:term

            self.output(f"adding new log")
            # update other stuff
            self.lastIndex = leaderIndex
            self.lastIndexTerm = term
            self.term = term
            self.leaderId = leaderId
            self.isPrimary = False

            # write in database
            self.redis.hset(self.hash_key, request.keyInput, request.valueInput)

            return raft_pb2.AppendEntriesResponse(term=self.term, success=True)

        else:  # if mismatch in logs, not successful
            self.output("there's a mismatch! need to reconcile")
            return raft_pb2.AppendEntriesResponse(term=self.term, success=False)

    # function to reconcile logs - called by primary
    def ReconcileLogs(self, request, context):
        if not self.shutdown_event.is_set():  # only do if server shutdown hasnt been activated
            path = request.filepath
            try:
                with open(path, 'r') as file1, open(self.log_file_path, 'r') as file2:

                    # read all lines from each log file
                    leader_lines = file1.readlines()
                    follower_lines = file2.readlines()

                    # reverse lists to start comparison from end of log
                    reversed1 = follower_lines[::-1]
                    reversed2 = leader_lines[::-1]

                    # find first index where lines match so we can copy all logs after 
                    match_index = None
                    for i, (line1, line2) in enumerate(zip(reversed1, reversed2)):
                        if line1 == line2:
                            match_index = i
                        else:
                            break

                    # find point to start appending from and up to
                    if match_index is not None:
                        # -1 because match_index is from the end
                        append_from = len(leader_lines) - match_index - 1
                    else:
                        append_from = 1  # no matches, copy all from leader besides online message

                    # write updated logs to secondary
                    with open(self.log_file_path, 'w') as file:
                        if follower_lines:
                            file.write(follower_lines[0])  # write the first line of secondary (online message)
                            if append_from < len(leader_lines):
                                file.writelines(leader_lines[append_from:])

                    # update the servers last logs so we can append entries in the future
                    self.lastIndex = request.prevLogIndex
                    self.lastIndexTerm = request.prevLogTerm
                    self.term = request.term
                    self.leaderId = request.leaderId
                    self.isPrimary = False

                self.output("reconciled logs!")

                return raft_pb2.ReconcileResponse(success=True)

            except:
                self.output("something went wrong when reconciling!")
                return raft_pb2.ReconcileResponse(success=False)

    # HEARTBEAT RELATED 

    # function to log heartbeat (called by servers)
    def Heartbeat(self, request, context):
        if self.shutdown_event.is_set():  # if already shut down, dont do anything!
            return
        id = request.service_identifier
        self.last_heartbeat[id] = time.time()  # log timestamp of heartbeat for the id received
        if id == self.leaderId:
            with open(self.heartbeat_file_path, "a") as file:  # update that alive in logs only when we get a heartbeat
                file.write(f"{id} is alive. Latest heartbeat received at {time.ctime(self.last_heartbeat[id])}\n")

        return empty_pb2.Empty()

    # function to send hearbeat to list of servers every 5 seconds
    def send_heartbeat(self):
        while not self.shutdown_event.is_set():  # do constantly until shutdown

            for name, channel in list(self.channels.items()):  # connect to other servers
                if self.shutdown_event.is_set():  # if already shut down, dont do anything!
                    break  # leave loop
                stub = raft_pb2_grpc.RAFTServiceStub(channel)
                try:
                    # send the heartbeat
                    stub.Heartbeat(raft_pb2.HeartbeatRequest(service_identifier=self.id))
                except:
                    self.output("------------------------------------------------")
                    self.output(f"Failed to send heartbeat to {name}.")

            # wait 20 sec between heartbeats
            time.sleep(self.heartbeat_timer)

    # function to check heartbeats received in case primary is down
    def check_heartbeat(self):
        while not self.shutdown_event.is_set():  # do constantly until shutdown
            current_time = time.time()
            for id, last_time in list(self.last_heartbeat.items()):

                if self.shutdown_event.is_set():  # if already shut down, dont do anything!
                    break  # leave loop

                if current_time - last_time > self.heartbeat_timer + 3 and id == self.leaderId:  # if has been 3s past expected heartbeat reception, it might be down
                    # log when we noticed the primary was down so we dont have multiple elections
                    self.primary_down_timestamp = time.time()

                    # if more than 5 sec passed, log that the server might be down
                    with open(self.heartbeat_file_path, "a") as file:
                        file.write(f"{id} might be down. Latest heartbeat received at {time.ctime(last_time)}\n")

                    # remove from tracking to avoid repeated logs
                    del self.last_heartbeat[id]
                    if not self.voted:
                        self.start_election_timer()  # start an election if you havent voted for someone already
                    else:
                        self.output("cant start a new election bc already voted!")

            time.sleep(1)  # lag to make sure things are up to date

    # ELECTION RELATED

    # function to start election once timer is up
    def start_election_timer(self):
        self.electionTimeout = random.uniform(150, 300)  # random timeout based on slides
        self.timer = threading.Timer(self.electionTimeout / 1000.0,
                                     self.become_candidate)  # after timer is up, become a candidate
        self.timer.start()

    # function to become a candidate and start requesting votes from other servers - activated after the randomized timeout
    def become_candidate(self):

        # if there has not been a shutdown process activated and it has not voted during the timeout time
        # and its been more than 5 seconds between when we noticed the primary was down and when we got a new primary announcement
        # note that this prevents back to back elections!

        if not self.shutdown_event.is_set() and not self.voted and self.primary_down_timestamp - self.primary_announcement_timestamp > 5:
            self.output("starting election!")
            self.isCandidate = True  # set self as candidate
            self.term += 1  # increase term
            self.voted = True  # set to true so you cant vote for anyone else
            votes = [1]  # vote for self
            self.voted = self.id

            for name, channel in list(self.channels.items()):  # connect to other servers
                stub = raft_pb2_grpc.RAFTServiceStub(channel)
                try:
                    # send the vote request
                    self.output(f"sending vote request to {name}!")
                    response = stub.RequestVote(
                        raft_pb2.VoteRequest(term=self.term, id=self.id, lastLogIndex=self.lastIndex,
                                             lastLogTerm=self.lastIndexTerm))
                    if response.voteGiven:
                        self.output(f"vote was received from {name}")
                        votes.append(1)  # if they voted append it to our list
                    elif response.term > self.term:  # if the response term is greater than our term, we have stale data and cant be the leader
                        self.isCandidate = False  # you cant be a candidate anymore
                except Exception as e:
                    self.output(f"Failed to send requestvote to {name}.")

            if sum(votes) > (
                    len(self.channels) + 1) / 2 and self.isCandidate:  # if we got majority vote and we're still a candidate
                self.output(f"won election with {sum(votes)} votes! updating info and sending appendentries rpcs")
                self.leaderId = self.id
                self.isPrimary = True
                self.isCandidate = False
                self.voted = False

                # you're the new leader so send an empty append entries message
                for name, channel in list(self.channels.items()):  # connect to other servers
                    stub = raft_pb2_grpc.RAFTServiceStub(channel)
                    try:
                        # send the empty appendentries request
                        response = stub.AppendEntries(
                            raft_pb2.AppendEntriesRequest(term=self.term, leaderId=self.id, prevLogIndex=self.lastIndex,
                                                          prevLogTerm=self.lastIndexTerm,
                                                          leaderCommit=-1))  # setting to -1 to indicate not an actual log entry
                    except Exception as e:
                        self.output(f"Failed to send post-vote appendentries to {name}.")
            else:
                self.output("did not win election")
                self.isPrimary = False
                self.isCandidate = False
                self.voted = False
                self.voted_for = ""

    # GRPC function to request votes from other servers. This function implements when the server receives a vote request containing the candidates term, id, and last log term + index
    # and returns a response to the requester based on some criteria
    def RequestVote(self, request, context):
        if not self.shutdown_event.is_set():
            self.output(f"vote was requested from {request.id}")
            candidateTerm = request.term
            candidateId = request.id
            candidateLastLogIndex = request.lastLogIndex
            candidateLastLogTerm = request.lastLogTerm

            # vote based on vote status and candidate info
            if self.term > candidateTerm or self.lastIndexTerm > candidateLastLogTerm or (
                    self.lastIndexTerm == candidateLastLogTerm and self.lastIndex > candidateLastLogIndex):
                self.output(f"did not vote for {candidateId}")
                return raft_pb2.VoteResponse(term=self.term, voteGiven=False)  # cant vote for them, their info is stale
            elif time.time() - self.primary_announcement_timestamp < 2:  # if JUST appointed new primary, dont vote
                self.output(f"recently appointed primary so did not vote for {candidateId}")
                return raft_pb2.VoteResponse(term=self.term, voteGiven=False)
            else:  # can vote for them
                if not self.voted:  # if we havent already voted for a candidate
                    self.voted = True
                    self.voted_for = candidateId
                    self.output(f"voted for {candidateId}")
                    return raft_pb2.VoteResponse(term=self.term, voteGiven=True)
                else:  # if we already voted we cant give our vote to this candidate
                    self.output(f"already voted for {self.voted_for} so cant vote for {candidateId}")
                    return raft_pb2.VoteResponse(term=self.term, voteGiven=False)

    # function to start the server
    def serve(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=30))
        raft_pb2_grpc.add_RAFTServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(f'[::]:{self.channel}')
        self.server.start()
        try:
            self.server.wait_for_termination()
        finally:
            self.stop()

    # function to stop the server
    def stop(self):
        if self.server:
            try:
                # stop all operations (including heartbeats)
                self.shutdown_event.set()  # signal all threads to stop
                self.server.stop(0)  # stop the server - allow active rpcs to finish (probably heartbeat for loops)

                self.server.wait_for_termination()  # wait server fully terminates

                # wait for all threads to finish
                self.send_heartbeat_thread.join()
                self.check_heartbeat_thread.join()

            except:
                print("something went wrong while shutting down")
