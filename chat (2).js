const WebSocketManager = {
    ws: null,
    reconnectAttempts: 0,

    init: function() {
        const userId = localStorage.getItem('currentUserId');
        if (!userId) return;

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

        this.ws.onopen = () => {
            this.send({ action: 'login', user_id: parseInt(userId) });
            // 新增：通知后端用户上线
            this.send({ action: 'web_online', user_id: parseInt(userId) });
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('WebSocket message error:', e);
            }
        };

        this.ws.onclose = () => {
            setTimeout(() => this.reconnect(), 1000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    },

    send: function(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    },

    reconnect: function() {
        if (this.reconnectAttempts < 5) {
            this.reconnectAttempts++;
            this.init();
        } else {
            alert('无法连接到服务器，请刷新页面重试');
        }
    },

// 修改后的 appendMessage 函数
    appendMessage: function(msg, type) {
        const container = document.getElementById('messageContainer');
        const div = document.createElement('div');
        div.className = `message ${type}`;
        
        // ========== 新增逻辑：与历史消息渲染保持一致 ==========
        let header = '';
        const isGroupChat = window.currentChat.type === 'group';

        // 群聊或接收消息显示发送者信息
        if (isGroupChat || type === 'received') {
            header = `
                <div class="message-header">
                    <div class="message-avatar">${String(msg.senderName).charAt(0)}</div>
                    <div class="message-sender">${isGroupChat && type === 'sent' ? '我' : msg.senderName}</div>
                </div>
            `;
        }

        div.innerHTML = `
            ${header}
            <div class="message-content">${escapeHtml(msg.content)}</div>
        `;
        // ==================================================

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    },

    handleMessage: function(data) {
        if (data.action === 'new_private_message') {
            this.handlePrivateMessage(data.message);
        } else if (data.action === 'new_group_message') {
            this.handleGroupMessage(data.message);
        }
    },

    handlePrivateMessage: function(message) {
        const currentUserId = parseInt(localStorage.getItem('currentUserId'));
        const chatTargetId = parseInt(window.currentChat.id);
        const isCurrentChat = window.currentChat.type === 'private' &&
            (
                (parseInt(message.sender_id) === chatTargetId && parseInt(message.receiver_id) === currentUserId) ||
                (parseInt(message.sender_id) === currentUserId && parseInt(message.receiver_id) === chatTargetId)
            );
        if (isCurrentChat) {
            this.renderMessage(message);
        }
    },

    handleGroupMessage: function(message) {
        const chatId = parseInt(window.currentChat.id);
        const isCurrentChat = window.currentChat.type === 'group' &&
            parseInt(message.receiver_id) === chatId;
        if (isCurrentChat) {
            this.renderMessage(message);
        }
    },

// 修改后的 renderMessage 函数
    renderMessage: function(rawMsg) {
        const currentUserId = parseInt(localStorage.getItem('currentUserId'), 10);
        const senderId = parseInt(rawMsg.sender_id);
        const receiverId = parseInt(rawMsg.receiver_id);

        // 核心判断逻辑：如果消息的发送者是自己，则显示为 sent，否则为 received
        const type = (senderId === currentUserId) ? 'sent' : 'received';

        let senderName = rawMsg.sender_name || (window.userMap && window.userMap[rawMsg.sender_id]) || `用户${rawMsg.sender_id}`;
        const msg = {
            type: type,
            sender: senderId,
            senderName: senderName,
            content: rawMsg.content
        };
        this.appendMessage(msg, msg.type);
    }
};

// 简单转义，防止XSS
function escapeHtml(str) {
    return String(str).replace(/[<>&"]/g, s => ({
        '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;'
    }[s]));
}

document.addEventListener('DOMContentLoaded', () => {
    WebSocketManager.init();

    window.sendMessage = function() {
        const input = document.querySelector('.message-input');
        const content = input.value.trim();
        if (!content) return;
        if (!window.currentChat.id) {
            alert('请先选择联系人或群聊');
            return;
        }
        const messageData = {
            action: 'send_message',
            sender_id: parseInt(localStorage.getItem('currentUserId')),
            receiver_type: window.currentChat.type,
            receiver_id: parseInt(window.currentChat.id),
            content: content
        };
        const success = WebSocketManager.send(messageData);
        if (success) {
            input.value = '';
            // 本地渲染自己发的消息
          
        }
    };

    document.querySelector('.send-button').addEventListener('click', window.sendMessage);
    document.querySelector('.message-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            window.sendMessage();
        }
    });
});

window.addEventListener('beforeunload', function () {
    const userId = localStorage.getItem('currentUserId');
    if (WebSocketManager.ws && WebSocketManager.ws.readyState === WebSocket.OPEN && userId) {
        // 通知后端用户下线
        WebSocketManager.send({ action: 'logout', user_id: parseInt(userId) });
        // 给 WebSocket 一点时间发送消息
        const start = Date.now();
        while (Date.now() - start < 100) {} // 简单阻塞100ms，确保消息发出
    }
});