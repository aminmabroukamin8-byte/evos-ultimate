import os
import sqlite3
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = 'evos_chat.db'

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
                       room TEXT DEFAULT 'عام',
                       text TEXT, type TEXT, url TEXT, filename TEXT, 
                       reply_to TEXT DEFAULT '', sender TEXT, time TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       task TEXT, status TEXT DEFAULT 'pending')''')
    conn.commit()
    conn.close()

init_db()

HTML_CODE = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVOS Ultimate Messenger & Hub</title>
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
        
        .rooms-bar { background: var(--input-bg); padding: 6px 15px; display: flex; gap: 8px; border-bottom: 1px solid var(--border-color); overflow-x: auto; align-items: center; justify-content: space-between; }
        .rooms-group { display: flex; gap: 8px; align-items: center; }
        .room-tab { padding: 4px 12px; border-radius: 12px; font-size: 12px; cursor: pointer; background: var(--bg-header); color: var(--text-color); border: 1px solid var(--border-color); white-space: nowrap; }
        .room-tab.active { background: #00a884; color: #fff; border-color: #00a884; }

        .header-actions { display: flex; gap: 6px; align-items: center; }
        .search-box { padding: 5px 10px; border-radius: 15px; border: none; background: var(--input-bg); color: var(--text-color); font-size: 13px; outline: none; }
        .btn-head { background: #2a3942; color: #fff; border: none; padding: 6px 12px; border-radius: 15px; cursor: pointer; font-size: 12px; font-weight: bold; }
        .btn-head:hover { background: #00a884; }

        .main-container { display: flex; flex: 1; overflow: hidden; position: relative; }
        .chat-section { flex: 1; display: flex; flex-direction: column; height: 100%; overflow: hidden; }
        
        .tasks-sidebar { width: 280px; background: var(--bg-header); border-left: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 10px; box-sizing: border-box; }
        .tasks-sidebar h3 { font-size: 14px; margin: 0 0 10px 0; color: #00a884; }
        .task-input-box { display: flex; gap: 5px; margin-bottom: 10px; }
        .task-input-box input { flex: 1; padding: 6px 10px; border-radius: 15px; border: none; background: var(--input-bg); color: var(--text-color); font-size: 12px; outline: none; }
        .task-input-box button { padding: 6px 10px; border-radius: 15px; font-size: 12px; }
        .tasks-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
        .task-item { background: var(--input-bg); padding: 8px 10px; border-radius: 6px; font-size: 12px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border-color); }
        .task-item.completed span { text-decoration: line-through; opacity: 0.6; }
        .task-actions span { cursor: pointer; margin-left: 5px; font-size: 11px; }

        .chat-box { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { background: var(--bg-msg); padding: 10px 15px; border-radius: 8px; max-width: 75%; align-self: flex-start; word-break: break-word; border: 1px solid var(--border-color); position: relative; }
        .msg.me { background: var(--bg-msg-me); align-self: flex-end; border: none; }
        
        .msg img { max-width: 100%; max-height: 250px; border-radius: 6px; display: block; margin-top: 5px; cursor: pointer; transition: transform 0.2s; }
        .msg img:hover { transform: scale(1.02); }
        .msg video { width: 100%; max-height: 250px; border-radius: 6px; display: block; margin-top: 5px; background: #000; }
        .msg audio { width: 260px; margin-top: 5px; outline: none; }
        .msg a { color: #53bdeb; text-decoration: none; font-weight: bold; }
        
        .quoted-box { background: rgba(0,0,0,0.15); border-right: 3px solid #00a884; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-bottom: 6px; color: var(--text-color); opacity: 0.9; }
        .link-preview { background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); padding: 8px; border-radius: 6px; margin-top: 5px; display: flex; flex-direction: column; gap: 3px; }
        .link-preview a { font-size: 13px; }

        .msg-tools { display: inline-flex; gap: 6px; margin-right: 8px; font-size: 11px; cursor: pointer; opacity: 0.7; }
        .msg-tools span:hover { opacity: 1; text-decoration: underline; }

        .typing-indicator { font-size: 11px; color: #00a884; padding: 0 15px 5px 15px; height: 15px; font-weight: bold; }

        .chat-input-area { background: var(--bg-header); padding: 10px; display: flex; gap: 8px; align-items: center; border-top: 1px solid var(--border-color); flex-direction: column; }
        .input-row { display: flex; gap: 8px; align-items: center; width: 100%; }
        
        .reply-preview-bar { display: none; width: 100%; background: var(--input-bg); padding: 6px 10px; border-radius: 8px; justify-content: space-between; align-items: center; font-size: 12px; border-right: 3px solid #00a884; }

        input[type="text"] { flex: 1; padding: 10px 15px; border: none; border-radius: 20px; outline: none; background: var(--input-bg); color: var(--text-color); font-size: 15px; }
        button, .icon-btn { background: #00a884; color: white; border: none; padding: 10px 14px; border-radius: 20px; cursor: pointer; font-weight: bold; display: flex; align-items: center; justify-content: center; }
        button:hover, .icon-btn:hover { background: #01755c; }
        .icon-btn { background: var(--input-bg); font-size: 16px; color: var(--text-color); }
        .mic-btn.recording { background: #ea0000; animation: pulse 1.2s infinite; }
        .timer-display { font-size: 12px; color: #ea0000; font-weight: bold; display: none; align-items: center; gap: 4px; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .time { font-size: 10px; color: #8696a0; text-align: left; margin-top: 4px; }
        #fileInput { display: none; }

        #lightbox { display: none; position: fixed; z-index: 999; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; }
        #lightbox img { max-width: 90%; max-height: 90%; border-radius: 8px; }

        @media(max-width: 768px) {
            .tasks-sidebar { display: none; }
        }
    </style>
</head>
<body>
    <div class="chat-header">
        <div class="header-left">
            <span>EVOS Ultimate Hub 🔒</span>
            <span class="status-indicator" title="متصل الآن"></span>
            <span class="status-text">متصل</span>
        </div>
        <div class="header-actions">
            <input type="text" class="search-box" id="searchInput" placeholder="بحث..." oninput="filterMessages()">
            <a href="/backup" class="btn-head" style="text-decoration: none;" title="تحميل نسخة احتياطية">💾 نسخة</a>
            <button class="btn-head" onclick="toggleTheme()">☀️/🌙</button>
            <button class="btn-head" onclick="fetchMessages(true)">تحديث 🔄</button>
        </div>
    </div>

    <div class="rooms-bar">
        <div class="rooms-group">
            <div class="room-tab active" onclick="switchRoom('عام')">💬 عام</div>
            <div class="room-tab" onclick="switchRoom('العمل')">💼 العمل والمشاريع</div>
            <div class="room-tab" onclick="switchRoom('ملاحظات')">📝 ملاحظات شخصية</div>
        </div>
    </div>
    
    <div class="main-container">
        <div class="chat-section">
            <div class="chat-box" id="chatBox"></div>
            <div class="typing-indicator" id="typingIndicator"></div>
            
            <div class="chat-input-area">
                <div class="reply-preview-bar" id="replyPreviewBar">
                    <span id="replyPreviewText"></span>
                    <span style="cursor: pointer; font-weight: bold;" onclick="cancelReply()">✕</span>
                </div>
                <div class="input-row">
                    <label for="fileInput" class="icon-btn" title="إرفاق ملف">📎</label>
                    <input type="file" id="fileInput" onchange="uploadFile()">
                    <button type="button" class="icon-btn" onclick="sendLocation()" title="إرسال موقعي الجغرافي">📍</button>
                    <button type="button" id="micBtn" class="icon-btn mic-btn" onclick="toggleRecordVoice()" title="تسجيل صوتي">🎙️</button>
                    <span id="timerDisplay" class="timer-display">🔴 <span id="secondsCount">0</span> ث</span>
                    <input type="text" id="messageInput" placeholder="اكتب رسالتك هنا أو الصق صورة (Ctrl+V)..." onpaste="handlePaste(event)" oninput="notifyTyping()" onkeypress="if(event.key === 'Enter') sendMessage()">
                    <button onclick="sendMessage()">إرسال</button>
                </div>
            </div>
        </div>

        <div class="tasks-sidebar">
            <h3>📌 مهامي وملاحظاتي</h3>
            <div class="task-input-box">
                <input type="text" id="taskInput" placeholder="مهمة جديدة..." onkeypress="if(event.key === 'Enter') addTask()">
                <button onclick="addTask()">إضافة</button>
            </div>
            <div class="tasks-list" id="tasksList"></div>
        </div>
    </div>

    <div id="lightbox" onclick="this.style.display='none'">
        <img id="lightboxImg" src="">
    </div>

    <script>
        if (Notification.permission !== "granted") { Notification.requestPermission(); }

        let lastMessageCount = 0;
        let allMessagesCache = [];
        let currentRoom = 'عام';
        let replyingToText = '';
        let recordingSeconds = 0;
        let timerInterval;

        function switchRoom(room) {
            currentRoom = room;
            document.querySelectorAll('.room-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            fetchMessages(true);
        }

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
                const res = await fetch(`/get_messages?room=${encodeURIComponent(currentRoom)}`);
                const messages = await res.json();
                allMessagesCache = messages;
                
                if (!isManual && messages.length === lastMessageCount) return;
                
                if (messages.length > lastMessageCount && lastMessageCount > 0) {
                    const latest = messages[messages.length - 1];
                    if (Notification.permission === "granted" && latest.sender !== 'أمين') {
                        new Notification(`رسالة جديدة في (${currentRoom})`, { body: `${latest.sender}: ${latest.text || 'مرفق جديد'}` });
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
                
                let toolsHTML = `
                    <div class="msg-tools">
                        <span onclick="setReply('${m.text ? m.text.replace(/'/g, "\\'").replace(/"/g, '&quot;') : 'مرفق'}')">↩️ رد</span>
                        ${m.sender === 'أمين' ? `<span onclick="editMessage(${m.id}, '${m.text ? m.text.replace(/'/g, "\\'").replace(/"/g, '&quot;') : ''}')">✏️</span> <span onclick="deleteMessage(${m.id})">🗑️</span>` : ''}
                    </div>
                `;

                let replyHTML = m.reply_to ? `<div class="quoted-box">رد على: ${m.reply_to}</div>` : '';
                let bodyHTML = `${replyHTML}<b>${m.sender}:</b> ${toolsHTML}`;
                
                if (m.type === 'image') {
                    bodyHTML += `<br><img src="${m.url}" alt="صورة" onclick="openLightbox('${m.url}')" onerror="this.onerror=null; this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'100\\'><rect width=\\'100%\\' height=\\'100%\\' fill=\\'%23222\\'/><text x=\\'50%\\' y=\\'50%\\' fill=\\'%23888\\' font-size=\\'12\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\'>صورة غير متوفرة</text></svg>';">`;
                } else if (m.type === 'video') {
                    const storageKey = 'video_time_' + m.url;
                    bodyHTML += `<br><video src="${m.url}" controls playsinline preload="auto" ontimeupdate="localStorage.setItem('${storageKey}', this.currentTime)" onloadedmetadata="this.currentTime = localStorage.getItem('${storageKey}') || 0"></video>`;
                } else if (m.type === 'audio') {
                    const audioKey = 'audio_time_' + m.url;
                    bodyHTML += `<br><audio src="${m.url}" controls preload="auto" ontimeupdate="localStorage.setItem('${audioKey}', this.currentTime)" onloadedmetadata="this.currentTime = localStorage.getItem('${audioKey}') || 0"></audio>`;
                } else if (m.type === 'file') {
                    bodyHTML += `<br>📁 <a href="${m.url}" target="_blank" download="${m.filename}">${m.filename || 'تحميل الملف'}</a>`;
                } else {
                    let formattedText = m.text;
                    const urlMatch = m.text.match(/(https?:\/\/[^\s]+)/g);
                    if (urlMatch && !m.text.includes('google.com/maps')) {
                        const link = urlMatch[0];
                        formattedText += `<div class="link-preview">🌐 <a href="${link}" target="_blank">${link}</a></div>`;
                    }
                    bodyHTML += `${formattedText}`;
                }
                
                bodyHTML += `<div class="time">${m.time}</div>`;
                div.innerHTML = bodyHTML;
                box.appendChild(div);
            });

            if (shouldScroll) { box.scrollTop = box.scrollHeight; }
        }

        function openLightbox(url) {
            document.getElementById('lightboxImg').src = url;
            document.getElementById('lightbox').style.display = 'flex';
        }

        function setReply(text) {
            replyingToText = text;
            document.getElementById('replyPreviewText').innerText = 'الرد على: ' + text;
            document.getElementById('replyPreviewBar').style.display = 'flex';
            document.getElementById('messageInput').focus();
        }

        function cancelReply() {
            replyingToText = '';
            document.getElementById('replyPreviewBar').style.display = 'none';
        }

        function notifyTyping() {
            fetch('/typing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ room: currentRoom, sender: 'أمين' })
            });
        }

        setInterval(async () => {
            try {
                const res = await fetch(`/get_typing?room=${encodeURIComponent(currentRoom)}`);
                const data = await res.json();
                const indicator = document.getElementById('typingIndicator');
                if (data.is_typing && data.sender !== 'أمين') {
                    indicator.innerText = `${data.sender} يكتب الآن...`;
                } else {
                    indicator.innerText = '';
                }
            } catch(e) {}
        }, 2000);

        function filterMessages() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            if (!query) { renderMessages(allMessagesCache, false); return; }
            const filtered = allMessagesCache.filter(m => (m.text && m.text.toLowerCase().includes(query)) || (m.filename && m.filename.toLowerCase().includes(query)));
            renderMessages(filtered, false);
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            if (!input.value.trim()) return;
            const text = input.value;
            const reply = replyingToText;
            input.value = '';
            cancelReply();
            
            await fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ room: currentRoom, text: text, type: 'text', reply_to: reply, sender: 'أمين' })
            });
            fetchMessages(true);
        }

        async function handlePaste(event) {
            const items = (event.clipboardData || event.originalEvent.clipboardData).items;
            for (let index in items) {
                let item = items[index];
                if (item.kind === 'file' && item.type.startsWith('image/')) {
                    event.preventDefault();
                    let blob = item.getAsFile();
                    let formData = new FormData();
                    formData.append('file', blob, 'clipboard_img_' + Date.now() + '.png');
                    let res = await fetch('/upload', { method: 'POST', body: formData });
                    let data = await res.json();
                    if (data.status === 'success') {
                        await fetch('/send_message', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ room: currentRoom, text: '', type: 'image', url: '/uploads/' + data.filename, filename: data.filename, reply_to: replyingToText, sender: 'أمين' })
                        });
                        cancelReply();
                        fetchMessages(true);
                    }
                }
            }
        }

        async function fetchTasks() {
            try {
                const res = await fetch('/get_tasks');
                const tasks = await res.json();
                const list = document.getElementById('tasksList');
                list.innerHTML = '';
                tasks.forEach(t => {
                    const div = document.createElement('div');
                    div.className = 'task-item' + (t.status === 'completed' ? ' completed' : '');
                    div.innerHTML = `
                        <span onclick="toggleTask(${t.id})" style="cursor: pointer; flex: 1;">${t.task}</span>
                        <div class="task-actions">
                            <span onclick="deleteTask(${t.id})">❌</span>
                        </div>
                    `;
                    list.appendChild(div);
                });
            } catch(e) {}
        }

        async function addTask() {
            const input = document.getElementById('taskInput');
            if (!input.value.trim()) return;
            const task = input.value;
            input.value = '';
            await fetch('/add_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task: task })
            });
            fetchTasks();
        }

        async function toggleTask(id) {
            await fetch('/toggle_task/' + id, { method: 'PUT' });
            fetchTasks();
        }

        async function deleteTask(id) {
            await fetch('/delete_task/' + id, { method: 'DELETE' });
            fetchTasks();
        }

        async function deleteMessage(id) {
            if (!confirm('حذف هذه الرسالة؟')) return;
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
            if (!navigator.geolocation) { alert('الموقع الجغرافي غير مدعوم.'); return; }
            navigator.geolocation.getCurrentPosition(async (pos) => {
                const locUrl = `https://www.google.com/maps?q=${pos.coords.latitude},${pos.coords.longitude}`;
                const text = `📍 موقعي الجغرافي: <a href="${locUrl}" target="_blank">فتح الخريطة</a>`;
                await fetch('/send_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ room: currentRoom, text: text, type: 'text', reply_to: '', sender: 'أمين' })
                });
                fetchMessages(true);
            }, () => { alert('تعذر جلب الموقع.'); });
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
                    body: JSON.stringify({ room: currentRoom, text: '', type: type, url: '/uploads/' + data.filename, filename: file.name, reply_to: replyingToText, sender: 'أمين' })
                });
                cancelReply();
                fetchMessages(true);
            }
            fileInput.value = '';
        }

        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        async function toggleRecordVoice() {
            const micBtn = document.getElementById('micBtn');
            const timerDisplay = document.getElementById('timerDisplay');
            const secondsCount = document.getElementById('secondsCount');
            
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    recordingSeconds = 0;
                    secondsCount.innerText = '0';
                    timerDisplay.style.display = 'flex';
                    
                    timerInterval = setInterval(() => {
                        recordingSeconds++;
                        secondsCount.innerText = recordingSeconds;
                    }, 1000);

                    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                    mediaRecorder.onstop = async () => {
                        clearInterval(timerInterval);
                        timerDisplay.style.display = 'none';
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
                                body: JSON.stringify({ room: currentRoom, text: '', type: 'audio', url: '/uploads/' + data.filename, filename: data.filename, reply_to: '', sender: 'أمين' })
                            });
                            fetchMessages(true);
                        }
                    };
                    mediaRecorder.start();
                    isRecording = true;
                    micBtn.classList.add('recording');
                } catch (err) { alert('تعذر الوصول للميكروفون.'); }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                micBtn.classList.remove('recording');
            }
        }

        fetchMessages(true);
        fetchTasks();
        setInterval(() => fetchMessages(false), 3000);
    </script>
</body>
</html>
'''

typing_states = {}

@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@app.route('/get_messages', methods=['GET'])
def get_messages():
    room = request.args.get('room', 'عام')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages WHERE room = ? ORDER BY id ASC', (room,))
    rows = cursor.fetchall()
    messages = []
    for row in rows:
        m = dict(row)
        m['text'] = decrypt_text(m['text'])
        m['reply_to'] = decrypt_text(m['reply_to'])
        messages.append(m)
    conn.close()
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    if data:
        cipher_text = encrypt_text(data.get('text', ''))
        cipher_reply = encrypt_text(data.get('reply_to', ''))
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (room, text, type, url, filename, reply_to, sender, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                       (data.get('room', 'عام'), cipher_text, data.get('type', 'text'), data.get('url', ''), data.get('filename', ''), cipher_reply, data.get('sender', 'أمين'), datetime.now().strftime('%H:%M')))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'}), 200
    return jsonify({'error': 'Invalid'}), 400

@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks ORDER BY id DESC')
    rows = cursor.fetchall()
    tasks = [dict(row) for row in rows]
    conn.close()
    return jsonify(tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    data = request.json
    if data and 'task' in data:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tasks (task) VALUES (?)', (data['task'],))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'}), 200
    return jsonify({'error': 'Invalid'}), 400

@app.route('/toggle_task/<int:task_id>', methods=['PUT'])
def toggle_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    if row:
        new_status = 'completed' if row[0] == 'pending' else 'pending'
        cursor.execute('UPDATE tasks SET status = ? WHERE id = ?', (new_status, task_id))
        conn.commit()
    conn.close()
    return jsonify({'status': 'updated'}), 200

@app.route('/delete_task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'}), 200

@app.route('/backup', methods=['GET'])
def backup_database():
    if os.path.exists(DB_PATH):
        return send_file(DB_PATH, as_attachment=True, download_name='evos_backup.db')
    return jsonify({'error': 'Not found'}), 404

@app.route('/typing', methods=['POST'])
def typing():
    data = request.json
    if data:
        room = data.get('room', 'عام')
        typing_states[room] = {'sender': data.get('sender', 'أمين'), 'time': datetime.now()}
        return jsonify({'status': 'ok'}), 200
    return jsonify({'error': 'Invalid'}), 400

@app.route('/get_typing', methods=['GET'])
def get_typing():
    room = request.args.get('room', 'عام')
    state = typing_states.get(room)
    if state and (datetime.now() - state['time']).seconds < 4:
        return jsonify({'is_typing': True, 'sender': state['sender']})
    return jsonify({'is_typing': False})

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