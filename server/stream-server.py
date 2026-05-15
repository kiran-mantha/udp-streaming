import json
import os
from flask import Flask, jsonify, render_template, send_from_directory

app = Flask(__name__)

BUFFER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'buffer')


@app.route('/')
@app.route('/live/')
def player():
    return render_template('player.html')


@app.route('/live/<path:filename>')
def serve_file(filename):
    return send_from_directory(BUFFER_DIR, filename)


@app.route('/stream/status')
def status():
    status_path = os.path.join(BUFFER_DIR, 'status.json')
    if os.path.exists(status_path):
        with open(status_path) as f:
            return jsonify(json.load(f))
    return jsonify({"status": "offline", "frames": 0, "uptime_seconds": 0})


if __name__ == '__main__':
    os.makedirs(BUFFER_DIR, exist_ok=True)
    print(f"Stream server: http://0.0.0.0:8080/live/")
    print(f"Buffer directory: {BUFFER_DIR}")
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
