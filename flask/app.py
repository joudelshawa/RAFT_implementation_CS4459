from flask import Flask, render_template, jsonify

app = Flask(__name__, template_folder='templates')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/load-server-content')
def load_server_content():
    content = render_template('server.html')
    return jsonify(html=content)


if __name__ == '__main__':
    app.run(debug=True)
