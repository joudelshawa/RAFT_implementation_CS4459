import subprocess
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='templates')
output = []
process = None


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/load-server-content')
def load_server_content():
    content = render_template('server.html')
    return jsonify(html=content)


@app.route('/toggle-server-manager', methods=['POST'])
def toggle_server():
    global process, output
    data = request.get_json()
    if data['status'] == 'on':
        if process is None:  # Start the process if not already started
            process = subprocess.Popen(['python', '../server_manager.py'], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, text=True, bufsize=1)
            output = []  # Reset output when starting a new process
            for line in iter(process.stdout.readline, ''):
                output.append(line)
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


if __name__ == '__main__':
    app.run(debug=True)
