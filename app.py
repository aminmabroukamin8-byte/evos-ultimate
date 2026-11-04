import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = 'evos_chat.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, type TEXT, url TEXT, filename TEXT, sender TEXT, time TEXT)''')
    conn.commit()
    conn.close()

init_db()

HTML_CODE = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVOS Ultimate Messenger</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #111b21; color: #e9edef; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; }
        .chat-header { background: #202c33; padding: 15px; font-size: 18px; font-weight: bold; text-align: center; border-bottom: 1px solid #222d34; display: flex; justify-content: space-between; align-items: center; }
        .refresh-btn { background: #2a3942; color: #fff; border: none; padding: 6px 14px; border-radius: 15px; cursor: pointer; font-size: 13px; font-weight: bold; }
        .refresh-btn:hover { background: #00a884; }
        .chat-box { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { background: #202c33; padding: 10px 15px; border-radius: 8px; max-width: 75%; align-self: flex-start; word-break: break-word; border: 1px solid #222d34; }
        .msg.me { background: #005c4b; align-self: flex-end; border: none; }
        .msg img { max-width: 100%; max-height: 250px; border-radius: 6px; display: block; margin-top: 5px; }
        .msg video { width: 100%; max-height: 250px; border-radius: 6px; display: block; margin-top: 5px; background: #000; }
        .msg audio { width: 260px; margin-top: 5px; outline: none; }
        .msg a { color: #53bdeb; text-decoration: none; font-weight: bold; }
        .chat-input-area { background: #202c33; padding: 10px; display: flex; gap: 8px; align-items: center; border-top: 1px solid #222d34; }
        input[type="text"] { flex: 1; padding: 10px 15px; border: none; border-radius: 20px; outline: none; background: #2a3942; color: #fff; font-size: 15px; }
        button, .attach-btn, .mic-btn { background: #00a884; color: white; border: none; padding: 10px 16px; border-radius: 20px; cursor: pointer; font-weight: bold; display: flex; align-items: center; justify-content: center; }
        button:hover, .attach-btn:hover, .mic-btn:hover { background: #01755c; }
        .attach-btn, .mic-btn { background: #2a3942; font-size: 18px; }
        .mic-btn.recording { background: #ea0000; animation: pulse 1.2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .time { font-size: 10px; color: #8696a0; text-align: left; margin-top: 4px; }
        #fileInput { display: none; }
    </style>
</head>
<body>
    <div class="chat-header">
        <span>EVOS Ultimate Messenger - متصل وآمن 🔒</span>
        <button class="refresh-btn" onclick="fetchMessages()">تحديث الرسائل يدوياً 🔄</button>
    </div>
    <div class="chat-box" id="chatBox"></div>
    <div class="chat-input-area">
        <label for="fileInput" class="attach-btn" title="إرفاق ملف">📎</label>
        <input type="file" id="fileInput" onchange="uploadFile()">
        <button type="button" id="micBtn" class="mic-btn" onclick="toggleRecordVoice()" title="تسجيل صوتي">🎙️</button>
        <input type="text" id="messageInput" placeholder="اكتب رسالتك هنا..." onkeypress="if(event.key === 'Enter') sendMessage()">
        <button onclick="sendMessage()">إرسال</button>
    </div>
    <script>
        let lastMessageCount = 0;
        async function fetchMessages() {
            try {
                const res = await fetch('/get_messages');
                const messages = await res.json();
                const box = document.getElementById('chatBox');
                
                // إذا كان عدد الرسائل هو نفسه، لا تقم بإعادة بناء الواجهة لتجنب إعادة تشغيل الفيديوهات
                if (messages.length === lastMessageCount) return;
                lastMessageCount = messages.length;
                
                box.innerHTML = '';
                messages.forEach(m => {
                    const div = document.createElement('div');
                    div.className = 'msg' + (m.sender === 'أمين' ? ' me' : '');
                    let bodyHTML = `<b>${m.sender}:</b> `;
                    if (m.type === 'image') {
                        bodyHTML += `<br><img src="${m.url}" alt="صورة">`;
                    } else if (m.type === 'video') {
                        bodyHTML += `<br><video src="${m.url}" controls playsinline preload="auto"></video>`;
                    } else if (m.type === 'audio') {
                        bodyHTML += `<br><audio src="${m.url}" controls preload="auto"></audio>`;
                    } else if (m.type === 'file') {
                        bodyHTML += `<br>📁 <a href="${m.url}" target="_blank" download="${m.filename}">${m.filename || 'تحميل الملف'}</a>`;
                    } else {
                        bodyHTML += `${m.text}`;
                    }
                    bodyHTML += `<div class="time">${m.time}</div>`;
                    div.innerHTML = bodyHTML;
                    box.appendChild(div);
                });
            } catch (e) { console.error(e); }
        }
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            if (!input.value.trim()) return;
            const text = input.value;
            input.value = '';
            await fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, type: 'text', sender: 'أمين' })
            });
            fetchMessages();
        }
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files.length) return;
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.status === 'success') {
                let type = 'file';
                if (file.type.startsWith('image/')) type = 'image';
                else if (file.type.startsWith('video/')) type = 'video';
                else if (file.type.startsWith('audio/')) type = 'audio';
                await fetch('/send_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: '', type: type, url: '/uploads/' + data.filename, filename: file.name, sender: 'أمين' })
                });
                fetchMessages();
            }
            fileInput.value = '';
        }
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        async function toggleRecordVoice() {
            const micBtn = document.getElementById('micBtn');
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        const fileName = 'voice_' + Date.now() + '.webm';
                        const formData = new FormData();
                        formData.append('file', audioBlob, fileName);
                        const res = await fetch('/upload', { method: 'POST', body: formData });
                        const data = await res.json();
                        if (data.status === 'success') {
                            await fetch('/send_message', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ text: '', type: 'audio', url: '/uploads/' + data.filename, filename: data.filename, sender: 'أمين' })
                            });
                            fetchMessages();
                        }
                    };
                    mediaRecorder.start();
                    isRecording = true;
                    micBtn.classList.add('recording');
                } catch (err) { alert('لا يمكن الوصول إلى الميكروفون.'); }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                micBtn.classList.remove('recording');
            }
        }
        fetchMessages();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@app.route('/get_messages', methods=['GET'])
def get_messages():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages ORDER BY id ASC')
    rows = cursor.fetchall()
    messages = [dict(row) for row in rows]
    conn.close()
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    if data:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (text, type, url, filename, sender, time) VALUES (?, ?, ?, ?, ?, ?)', (data.get('text', ''), data.get('type', 'text'), data.get('url', ''), data.get('filename', ''), data.get('sender', 'أمين'), datetime.now().strftime('%H:%M')))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'}), 200
    return jsonify({'error': 'Invalid'}), 400

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file and file.filename:
        safe_filename = file.filename.replace(' ', '_')
        file.save(os.path.join(UPLOAD_FOLDER, safe_filename))
        return jsonify({'status': 'success', 'filename': safe_filename}), 200
    return jsonify({'error': 'Failed'}), 400

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    res = send_from_directory(UPLOAD_FOLDER, filename)
    res.headers.add('Accept-Ranges', 'bytes')
    return res

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)