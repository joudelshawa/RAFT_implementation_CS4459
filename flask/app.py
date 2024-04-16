import subprocess
from flask import Flask, render_template, request, jsonify
import threading
import os

app = Flask(__name__, template_folder='templates')
output = []
process = None


@app.route('/')
def home():
    return render_template('home.html')


def log_files_exist(server_id):
    # filenames = [f"log_Server {server_id}.txt", f"heartbeat_Server {server_id}.txt", f"output_Server {server_id}.txt"]
    filenames = [f"log_Server {server_id}.txt", f"output_Server {server_id}.txt"]

    return all(os.path.exists(filename) for filename in filenames)


@app.route('/check-logs', methods=['POST'])
def check_logs():
    server_id = request.json['server_id']
    if log_files_exist(server_id):
        return jsonify({'status': 'Connected'})
    return jsonify({'status': 'Log files not found'})


@app.route('/get-log', methods=['POST'])
def get_log():
    server_id = request.json['server_id']
    log_type = request.json['log_type']  # "log", "heartbeat", or "output"
    filename = f"{log_type}_Server {server_id}.txt"
    try:
        with open(filename, 'r') as file:
            content = file.read()
        return jsonify({'content': content})
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


def read_output(proc, out):
    """Read process output and append to the output list."""
    try:
        for line in iter(proc.stdout.readline, ''):
            out.append(line)
    finally:
        proc.stdout.close()


@app.route('/toggle-server-manager', methods=['POST'])
def toggle_server():
    global process, output
    data = request.get_json()
    if data['status'] == 'on':
        if process is None:  # Start the process if not already started
            process = subprocess.Popen(['python', '../server_manager.py'], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            output = []  # Reset output when starting a new process

            # Create a thread to read the output of the process
            threading.Thread(target=read_output, args=(process, output), daemon=True).start()
        return jsonify({'message': 'Server Manager started'})
    elif data['status'] == 'off':
        if process:
            process.stdin.write('q\n')
            process.stdin.flush()
            process.communicate()
            process = None
        return jsonify({'message': 'Server Manager stopped'})

    return jsonify({'error': 'Invalid command'}), 400


@app.route('/get-output', methods=['GET'])
def get_output():
    global output
    return jsonify({'output': output})


@app.route('/send-command', methods=['POST'])
def send_command():
    global process
    if process and process.poll() is None:  # Check if the process is still running
        data = request.get_json()
        try:
            process.stdin.write(data['command'] + '\n')
            process.stdin.flush()
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        return jsonify({'message': 'Command sent'})
    else:
        return jsonify({'error': 'Server not running'}), 400


@app.route('/start-server', methods=['POST'])
def start_server():
    global process
    server_id = request.json.get('server_id')
    if process and process.poll() is None:
        try:
            command = f'start server {server_id}'
            process.stdin.write(command + '\n')
            process.stdin.flush()
            return jsonify({'message': f'Command "{command}" sent to server manager'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Server manager is not running'}), 400


@app.route('/get-primary', methods=['GET'])
def get_primary():
    global process
    if process and process.poll() is None:
        try:
            process.stdin.write('get primary\n')
            process.stdin.flush()
            return jsonify({'message': 'Command sent'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Server manager is not running'}), 400


if __name__ == '__main__':
    app.run(debug=True)
