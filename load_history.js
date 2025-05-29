// main_program.js
document.addEventListener('DOMContentLoaded', function() {
    const currentUserId = localStorage.getItem('currentUserId');
    if (!currentUserId) {
        window.location.href = '/init/sign_in'; // 跳转登录页
        return;
    }
    window.currentChat = { id: null, type: 'private' }; 

    // 事件监听初始化
    initEventListeners();
    
    // 初始加载
    loadContactLists('private');
    loadChatMessages();
    updateUserInfo();
});

function initEventListeners() {
    // 栏目切换
    document.querySelectorAll('.contact-tab-item').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.contact-tab-item').forEach(t => 
                t.classList.remove('active'));
            this.classList.add('active');
            loadContactLists(this.dataset.type);
        });
    });
}

function renderContactList(data, type) {
    window.userMap = window.userMap || {};
    data.forEach(item => {
        window.userMap[item.user_id] = item.username || item.group_name;
    });
    const container = document.querySelector('.contact-items');
    container.innerHTML = '';
    const currentUserId = localStorage.getItem('currentUserId');

    // 过滤掉自己
    const filtered = data.filter(item => {
        // 私聊：item.user_id，群聊：不过滤
        if (type === 'user' || type === 'private') {
            return String(item.user_id) !== String(currentUserId);
        }
        return true;
    });

    filtered.forEach(item => {
        const div = document.createElement('div');
        div.className = 'contact-item';
        div.dataset.id = item[type + '_id'];
        div.dataset.type = type;
        div.innerHTML = `
            <div class="contact-avatar">${item.username?.charAt(0) || item.group_name?.charAt(0)}</div>
            <div class="contact-info">
                <div class="contact-name">${item.username || item.group_name}</div>
            </div>
        `;
        
        div.addEventListener('click', function() {
            document.querySelectorAll('.contact-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            window.currentChat = {
                id: this.dataset.id,
                type: type === 'user' ? 'private' : 'group'
            };
            loadChatMessages();
            updateChatHeader();
        });
        
        container.appendChild(div);
    });
}
// 新增聊天窗口标题更新
function updateChatHeader() {
    const header = document.querySelector('.chat-title');
    const activeItem = document.querySelector('.contact-item.active');
    if (activeItem) {
        header.textContent = activeItem.querySelector('.contact-name').textContent;
    }
}

// 联系人列表加载（XHR版）
function loadContactLists(type) {
    const container = document.querySelector('.contact-items');
    container.innerHTML = '<div class="loading">加载中...</div>';

    let url;
    if (type === 'private') {
        url = 'http://192.168.3.232:80/history/users';
    } else {
        const userId = localStorage.getItem('currentUserId');
        url = `http://192.168.3.232:80/history/groups?user_id=${userId}`;
    }

    const xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                renderContactList(data, type === 'private' ? 'user' : 'group');
            } else {
                showError('加载失败: ' + xhr.status);
            }
        }
    };
    xhr.onerror = function() {
        showError('网络错误');
    };
    xhr.send();
}

// 消息加载（XHR版）
function loadChatMessages() {
    const container = document.getElementById('messageContainer');
    container.innerHTML = '<div class="loading">加载消息中...</div>';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://192.168.3.232:80/history/messages', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                const messages = JSON.parse(xhr.responseText);
                processMessages(messages);
                renderChatMessages(messages);
            } else {
                showError('消息加载失败: ' + xhr.status);
            }
        }
    };
    
    const postData = JSON.stringify({
        userId: localStorage.getItem('currentUserId'),
        chatId: window.currentChat.id,
        type: window.currentChat.type,
        page: 1,
        pageSize: 50
    });
    
    xhr.send(postData);
}


function processMessages(messages) {
    const currentUserId = parseInt(localStorage.getItem('currentUserId'), 10);
    messages.forEach(msg => {
        // 使用 sender_id 判断发送者身份
        msg.sender = msg.sender_name || window.userMap[msg.sender_id] || `用户${msg.sender_id}`;
        // 确保 type 字段正确（根据实际需要，可选）
        msg.type = (parseInt(msg.sender_id) === currentUserId) ? 'sent' : 'received';
    });
}


// load_history.js - 修改后的 renderChatMessages 函数
function renderChatMessages(messages) {
    const container = document.getElementById('messageContainer');
    container.innerHTML = '';
    
    const reversedMessages = [...messages].reverse();

    reversedMessages.forEach(msg => {
        const div = document.createElement('div');
        div.className = `message ${msg.type}`;
    


        // ====================== 新增逻辑 ======================

        
        // 2. 群聊消息头显示逻辑
        let header = '';
        const isGroupChat = window.currentChat.type === 'group';
        
        if (isGroupChat && msg.type === 'received') {
            // 群聊接收消息：显示发送者信息
            header = `
                <div class="message-header">
                    <div class="message-avatar">${msg.sender?.charAt(0) || ''}</div>
                    <div class="message-sender">${msg.sender || ''}</div>
                </div>
            `;
        } else if (isGroupChat && msg.type === 'sent') {
            // 群聊自己发送的消息：显示发送者信息（可选，根据需求注释）
            header = `
                <div class="message-header">
                    <div class="message-avatar">${msg.sender?.charAt(0) || ''}</div>
                    <div class="message-sender">我</div>
                </div>
            `;
        } else if (msg.type === 'received') {
            // 私聊接收消息：显示发送者信息
            header = `
                <div class="message-header">
                    <div class="message-avatar">${msg.sender?.charAt(0) || ''}</div>
                    <div class="message-sender">${msg.sender || ''}</div>
                </div>
            `;
        }

        // ====================== 消息内容渲染 ======================
        div.innerHTML = `
            ${header}
            <div class="message-content">${msg.content}</div>

        `;

        container.appendChild(div);
    });

    container.scrollTop = container.scrollHeight; // 确保滚动到底部
}

// 用户信息加载（XHR版）
function updateUserInfo() {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', `http://192.168.3.232:80/history/user_info?id=${localStorage.getItem('currentUserId')}`, true);
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {
            const user = JSON.parse(xhr.responseText);
            document.querySelector('.user-name').textContent = user.username;
            document.querySelector('.user-avatar').textContent = user.username.charAt(0);
        }
    };
    
    xhr.send();
}

// 错误处理
function showError(msg) {
    const container = document.getElementById('messageContainer');
    container.innerHTML = `<div class="error">${msg}</div>`;
}