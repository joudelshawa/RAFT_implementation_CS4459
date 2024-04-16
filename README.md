This repository contains code that is based on the RAFT Algorithm for a Primary-Backup System. We have provided a way to interact with the system via terminal or using a Flask app. Please see the instructions below to run the system:

### Run via Terminal
1. Clone this repository locally using `git clone https://github.com/joudelshawa/RAFT_implementation_CS4459.git` 
2. In your local location, run `pip install -r requirements.txt`
3. Ensure redis is on using `redis-server` 
4. Then run `python server_manager.py` and play around with the system! You can add servers using `start server 1`, where 1 can be replaced with any positive integer, remove servers using `stop server 1` or `stop all`, and input (write) data using `input key value`, where *key* and *value* can be any strings.

### Run Flask App
**Do NOT force shut down the Flask App before killing all active servers!**
1. Clone this repository locally using `git clone https://github.com/joudelshawa/RAFT_implementation_CS4459.git` 
2. In your local location, run `pip install -r requirements.txt`
3. Ensure redis is on using `redis-server` 
4. Run `cd flask`
5. Run `python app.py` and open the corresponding localhost link (e.g., `http://127.0.0.1:5000`) and start playing around with the system! You can add servers using the `add server` button, which will automatically add new servers without needing server IDs (they will monotonically increase), remove servers using the `kill server` button on each server card, and input (write) data using the `input` bar by providing `key value` and pressing enter, where *key* and *value* can be any strings.


Happy logging!

Authors:
* Joud El-Shawa
* Samuel Catania
* Meg Zhang
* Ian Prentice
