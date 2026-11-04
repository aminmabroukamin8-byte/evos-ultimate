import os
import sqlite3
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = 'evos_chat.db'

# دالة بسيطة للتشفير وفك التشفير محلياً (Base64 Safe Layer)
def encrypt_text(text):
    if not text: return ""
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def decrypt_text(cipher_text):
    if not cipher_text: return ""
    try:
        return base64.b64decode(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception:
        return cipher_text

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       text TEXT, type TEXT, url TEXT, filename TEXT, sender TEXT, time TEXT)''')
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
        :root {
            --bg-body: #111b21;
            --bg-header: #202c33;
            --bg-msg: #202c33;
            --bg-msg-me: #005c4b;
            --text-color: #e9edef;
            --border-color: #222d34;
            --input-bg: #2a3942;
        }

        body.light-mode {
            --bg-body: #efeae2;
            --bg-header: #f0f2f5;
            --bg-msg: #ffffff;
            --bg-msg-me: #d9fdd3;
            --text-color: #111b21;
            --border-color: #e0e0e0;
            --input-bg: #ffffff;
        }

        body { font-family: Tahoma, sans-serif; background: var(--bg-body); color: var(--text-color); margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; transition: background 0.3s, color 0.3s; }
        .chat-header { background: var(--bg-header); padding: 10px 15px; font-size: 16px; font-weight: bold; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
        .header-left { display: flex; align-items: center; gap: 8px; }
        .status-indicator { width: 10px; height: 10px; background-color: #00a884; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #00a884; }
        .status-text { font-size: 12px; color: #8696a0; font-weight: normal; }
        
        .header-actions { display: flex; gap: 6px; align-items: center; }
        .search-box { padding: 5px 10px; border-radius: 15px; border: none; background: var(--input-bg); color: var(--text-color); font-size: 13px; outline: none; }
        .btn-head { background: #2a3942; color: #fff; border: none; padding: 6px 12px; border-radius: 15px; cursor: pointer; font-size: 12px; font-weight: bold; }
        .btn-head:hover { background: #00a884; }

        .chat-box { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { background: var(--bg-msg); padding: 10px 15px; border-radius: 8px; max-width: 75%; align-self: flex-start; word-break: break-word; border: 1px solid var(--border-color); position: relative; }
        .msg.me { background: var(--bg-msg-me); align-self: flex-end; border: none; }
        .msg img { max-width: 100%; max-height: 250px; border-radius: 6px; display: block; margin-top: 5px; }
        .msg video { width: 100%; max-height: 250px; border-radius: 6px; display: block; margin-top: 5px; background: #000; }
        .msg audio { width: 260px; margin-top: 5px; outline: none; }
        .msg a { color: #53bdeb; text-decoration: none; font-weight: bold; }
        
        .msg-tools { display: inline-flex; gap: 6px; margin-right: 8px; font-size: 11px; cursor: pointer; opacity: 0.7; }
        .msg-tools span:hover { opacity: 1; text-decoration: underline; }

        .chat-input-area { background: var(--bg-header); padding: 10px; display: flex; gap: 8px; align-items: center; border-top: 1px solid var(--border-color); }
        input[type="text"] { flex: 1; padding: 10px 15px; border: none; border-radius: 20px; outline: none; background: var(--input-bg); color: var(--text-color); font-size: 15px; }
        button, .icon-btn { background: #00a884; color: white; border: none; padding: 10px 14px; border-radius: 20px; cursor: pointer; font-weight: bold; display: flex; align-items: center; justify-content: center; }
        button:hover, .icon-btn:hover { background: #01755c; }
        .icon-btn { background: var(--input-bg); font-size: 16px; color: var(--text-color); }
        .mic-btn.recording { background: #ea0000; animation: pulse 1.2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .time { font-size: 10px; color: #8696a0; text-align: left; margin-top: 4px; }
        #fileInput { display: none; }
    </style>
</head>
<body>
    <div class="chat-header">
        <div class="header-left">
            <span>EVOS Ultimate 🔒</span>
            <span class="status-indicator" title="متصل الآن"></span>
            <span class="status-text">متصل</span>
        </div>
        <div class="header-actions">
            <input type="text" class="search-box" id="searchInput" placeholder="بحث..." oninput="filterMessages()">
            <button class="btn-head" onclick="toggleTheme()">☀️/🌙</button>
            <button class="btn-head" onclick="fetchMessages(true)">تحديث 🔄</button>
        </div>
    </div>
    
    <div class="chat-box" id="chatBox"></div>
    
    <div class="chat-input-area">
        <label for="fileInput" class="icon-btn" title="إرفاق ملف">📎</label>
        <input type="file" id="fileInput" onchange="uploadFile()">
        <button type="button" class="icon-btn" onclick="sendLocation()" title="إرسال موقعي الجغرافي">📍</button>
        <button type="button" id="micBtn" class="icon-btn mic-btn" onclick="toggleRecordVoice()" title="تسجيل صوتي">🎙️</button>
        <input type="text" id="messageInput" placeholder="اكتب رسالتك هنا..." onkeypress="if(event.key === 'Enter') sendMessage()">
        <button onclick="sendMessage()">إرسال</button>
    </div>

    <script>
        if (Notification.permission !== "granted") {
            Notification.requestPermission();
        }

        let lastMessageCount = 0;
        let allMessagesCache = [];

        function toggleTheme() {
            document.body.classList.toggle('light-mode');
            const isLight = document.body.classList.contains('light-mode');
            localStorage.setItem('evos_theme', isLight ? 'light' : 'dark');
        }

        if (localStorage.getItem('evos_theme') === 'light') {
            document.body.classList.add('light-mode');
        }

        async function fetchMessages(isManual = false) {
            try {
                const res = await fetch('/get_messages');
                const messages = await res.json();
                allMessagesCache = messages;
                
                if (!isManual && messages.length === lastMessageCount) return;
                
                if (messages.length > lastMessageCount && lastMessageCount > 0) {
                    const latest = messages[messages.length - 1];
                    if (Notification.permission === "granted" && latest.sender !== 'أمين') {
                        new Notification("رسالة جديدة في EVOS", { body: `${latest.sender}: ${latest.text || 'مرفق جديد'}` });
                    }
                }

                lastMessageCount = messages.length;
                renderMessages(messages, isManual);
            } catch (e) { console.error(e); }
        }

        function renderMessages(messages, shouldScroll = false) {
            const box = document.getElementById('chatBox');
            box.innerHTML = '';

            messages.forEach(m => {
                const div = document.createElement('div');
                div.className = 'msg' + (m.sender === 'أمين' ? ' me' : '');
                
                let toolsHTML = m.sender === 'أمين' ? `
                    <div class="msg-tools">
                        <span onclick="editMessage(${m.id}, '${m.text.replace(/'/g, "\\'")}')">✏️</span>
                        <span onclick="deleteMessage(${m.id})">🗑️</span>
                    </div>
                ` : '';

                let bodyHTML = `<b>${m.sender}:</b> ${toolsHTML}`;
                
                if (m.type === 'image') {
                    bodyHTML += `<br><img src="${m.url}" alt="صورة" onerror="this.onerror=null; this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'100\\'><rect width=\\'100%\\' height=\\'100%\\' fill=\\'%23222\\'/><text x=\\'50%\\' y=\\'50%\\' fill=\\'%23888\\' font-size=\\'12\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\'>صورة غير متوفرة</text></svg>';">`;
                } else if (m.type === 'video') {
                    const storageKey = 'video_time_' + m.url;
                    bodyHTML += `<br><video src="${m.url}" controls playsinline preload="auto" ontimeupdate="localStorage.setItem('${storageKey}', this.currentTime)" onloadedmetadata="this.currentTime = localStorage.getItem('${storageKey}') || 0"></video>`;
                } else if (m.type === 'audio') {
                    const audioKey = 'audio_time_' + m.url;
                    bodyHTML += `<br><audio src="${m.url}" controls preload="auto" ontimeupdate="localStorage.setItem('${audioKey}', this.currentTime)" onloadedmetadata="this.currentTime = localStorage.getItem('${audioKey}') || 0"></audio>`;
                } else if (m.type === 'file') {
                    bodyHTML += `<br>📁 <a href="${m.url}" target="_blank" download="${m.filename}">${m.filename || 'تحميل الملف'}</a>`;
                } else {
                    bodyHTML += `${m.text}`;
                }
                
                bodyHTML += `<div class="time">${m.time}</div>`;
                div.innerHTML = bodyHTML;
                box.appendChild(div);
            });

            if (shouldScroll) {
                box.scrollTop = box.scrollHeight;
            }
        }

        function filterMessages() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            if (!query) {
                renderMessages(allMessagesCache, false);
                return;
            }
            const filtered = allMessagesCache.filter(m => m.text.toLowerCase().includes(query) || (m.filename && m.filename.toLowerCase().includes(query)));
            renderMessages(filtered, false);
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
            fetchMessages(true);
        }

        async function deleteMessage(id) {
            if (!confirm('هل تريد حذف هذه الرسالة؟')) return;
            await fetch('/delete_message/' + id, { method: 'DELETE' });
            fetchMessages(true);
        }

        async function editMessage(id, oldText) {
            const newText = prompt('تعديل الرسالة:', oldText);
            if (newText !== null && newText.trim() !== '') {
                await fetch('/edit_message/' + id, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: newText.trim() })
                });
                fetchMessages(true);
            }
        }

        function sendLocation() {
            if (!navigator.geolocation) {
                alert('ميزة الموقع الجغرافي غير مدعومة في متصفحك.');
                return;
            }
            navigator.geolocation.getCurrentPosition(async (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const locUrl = `https://www.google.com/maps?q=${lat},${lon}`;
                const text = `📍 موقعي الجغرافي: <a href="${locUrl}" target="_blank">فتح الخريطة</a>`;
                await fetch('/send_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, type: 'text', sender: 'أمين' })
                });
                fetchMessages(true);
            }, () => { alert('تعذر الحصول على الموقع الجغرافي.'); });
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
                fetchMessages(true);
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
                            fetchMessages(true);
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

        fetchMessages(true);
        setInterval(() => fetchMessages(false), 3000);
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
    messages = []
    for row in rows:
        m = dict(row)
        m['text'] = decrypt_text(m['text'])  # فك التشفير التلقائي عند العرض
        messages.append(m)
    conn.close()
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    if data:
        cipher_text = encrypt_text(data.get('text', ''))  # تشفير النص قبل التخزين
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (text, type, url, filename, sender, time) VALUES (?, ?, ?, ?, ?, ?)', 
                       (cipher_text, data.get('type', 'text'), data.get('url', ''), data.get('filename', ''), data.get('sender', 'أمين'), datetime.now().strftime('%H:%M')))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'}), 200
    return jsonify({'error': 'Invalid'}), 400

@app.route('/edit_message/<int:msg_id>', methods=['PUT'])
def edit_message(msg_id):
    data = request.json
    if data and 'text' in data:
        cipher_text = encrypt_text(data['text'])
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE messages SET text = ? WHERE id = ?', (cipher_text, msg_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'updated'}), 200
    return jsonify({'error': 'Invalid'}), 400

@app.route('/delete_message/<int:msg_id>', methods=['DELETE'])
def delete_message(msg_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE id = ?', (msg_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'}), 200

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