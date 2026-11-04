import os, sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = 'evos_chat.db'

@app.route('/')
def index():
    return '<h1>EVOS Messenger Online</h1>'

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    res = send_from_directory(UPLOAD_FOLDER, filename)
    res.headers.add('Accept-Ranges', 'bytes')
    return res

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
