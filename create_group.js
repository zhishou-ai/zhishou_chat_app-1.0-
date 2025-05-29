// 添加群组创建相关功能
document.querySelector('.group-create-btn').addEventListener('click', function() {
    showCreateGroupModal();
});

// 显示创建群组模态框
function showCreateGroupModal() {
    const modal = document.querySelector('.group-modal');
    modal.style.display = 'flex';
    
    // 加载所有用户
    loadAllUsers().then(users => {
        const container = document.querySelector('.friend-list');
        container.innerHTML = '<h4>选择成员：</h4>';
        
        users.forEach(user => {
            if(user.user_id == localStorage.getItem('currentUserId')) return;
            
            const div = document.createElement('div');
            div.className = 'friend-item';
            div.innerHTML = `
                <label>
                    <input type="checkbox" value="${user.user_id}">
                    ${user.username} (ID: ${user.user_id})
                </label>
            `;
            container.appendChild(div);
        });
    });

    // 关闭模态框事件
    modal.querySelector('.close-modal').addEventListener('click', () => modal.style.display = 'none');
    modal.querySelector('.cancel-btn').addEventListener('click', () => modal.style.display = 'none');
    
    // 提交创建事件
    modal.querySelector('.create-btn').addEventListener('click', createGroup);
}

// 获取所有用户
function loadAllUsers() {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('GET', 'http://192.168.3.232:80/history/users');
        xhr.onload = () => {
            if(xhr.status === 200) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject();
            }
        };
        xhr.send();
    });
}

// 创建群组
function createGroup() {
    const modal = document.querySelector('.group-modal');
    const groupName = document.getElementById('groupName').value.trim();
    const checked = Array.from(modal.querySelectorAll('input[type="checkbox"]:checked'))
                      .map(input => parseInt(input.value));

    // 前端验证
    if (!groupName) {
        showError('请输入群名称');
        return;
    }
    if (groupName.length < 2 || groupName.length > 64) {
        showError('群名称需要2-64个字符');
        return;
    }
    if (checked.length === 0) {
        showError('请至少选择一位成员');
        return;
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://192.168.3.232:80/create_group');
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onload = function() {
        const response = JSON.parse(xhr.responseText || '{}');
        if (xhr.status === 200 && response.success) {
            modal.style.display = 'none';
            // 强制刷新群组列表
            const groupTab = document.querySelector('[data-type="group"]');
            groupTab.click();
            setTimeout(() => groupTab.click(), 100); // 双重刷新确保数据更新
        } else {
            showError(response.error || '未知错误');
        }
    };

    xhr.onerror = function() {
        showError('网络连接失败');
    };

    xhr.send(JSON.stringify({
        creator_id: parseInt(localStorage.getItem('currentUserId')),
        group_name: groupName,
        members: checked
    }));
}

function showError(msg) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = msg;
    
    const modalBody = document.querySelector('.modal-body');
    const existingError = modalBody.querySelector('.error-message');
    if (existingError) existingError.remove();
    
    modalBody.prepend(errorDiv);
    setTimeout(() => errorDiv.remove(), 3000);
}