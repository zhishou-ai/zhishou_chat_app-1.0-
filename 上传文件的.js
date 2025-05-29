// 文件上传功能
document.addEventListener('DOMContentLoaded', function() {
    const fileUpload = document.getElementById('fileUpload');
    const previewArea = document.getElementById('previewArea');
    const messageInput = document.querySelector('.message-input');
    const sendButton = document.querySelector('.send-button');
    const imagePreviewModal = document.getElementById('imagePreviewModal');
    const previewedImage = document.getElementById('previewedImage');
    const closePreview = document.querySelector('.close-preview');
    
    let filesToSend = [];
    
    // 文件上传按钮点击事件
    document.querySelector('.file-upload-btn').addEventListener('click', function(e) {
        e.preventDefault();
        fileUpload.click();
    });
    
    // 文件选择变化事件
    fileUpload.addEventListener('change', function(e) {
        const files = e.target.files;
        if (files.length > 0) {
            Array.from(files).forEach(file => {
                if (!filesToSend.some(f => f.name === file.name && f.size === file.size)) {
                    filesToSend.push(file);
                    renderPreview(file);
                }
            });
            fileUpload.value = ''; // 重置input以便选择相同文件
        }
    });
    
    // 渲染文件预览
    function renderPreview(file) {
        const previewItem = document.createElement('div');
        previewItem.className = 'preview-item';
        
        if (file.type.startsWith('image/')) {
            // 图片预览
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.onclick = () => openImagePreview(e.target.result);
                
                const removeBtn = document.createElement('div');
                removeBtn.className = 'remove-file';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = (e) => {
                    e.stopPropagation();
                    removeFile(file, previewItem);
                };
                
                previewItem.appendChild(img);
                previewItem.appendChild(removeBtn);
            };
            reader.readAsDataURL(file);
        } else {
            // 普通文件预览
            const filePreview = document.createElement('div');
            filePreview.className = 'file-preview';
            
            const fileIcon = document.createElement('div');
            fileIcon.className = 'file-icon';
            fileIcon.innerHTML = '<i class="fas fa-file"></i>';
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';
            
            const fileName = document.createElement('div');
            fileName.className = 'file-name';
            fileName.textContent = file.name;
            
            const fileSize = document.createElement('div');
            fileSize.className = 'file-size';
            fileSize.textContent = formatFileSize(file.size);
            
            fileInfo.appendChild(fileName);
            fileInfo.appendChild(fileSize);
            
            const removeBtn = document.createElement('div');
            removeBtn.className = 'remove-file';
            removeBtn.innerHTML = '×';
            removeBtn.onclick = (e) => {
                e.stopPropagation();
                removeFile(file, previewItem);
            };
            
            filePreview.appendChild(fileIcon);
            filePreview.appendChild(fileInfo);
            previewItem.appendChild(filePreview);
            previewItem.appendChild(removeBtn);
        }
        
        previewArea.appendChild(previewItem);
    }
    
    // 移除文件
    function removeFile(file, previewItem) {
        filesToSend = filesToSend.filter(f => !(f.name === file.name && f.size === file.size));
        previewItem.remove();
    }
    
    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // 发送消息和文件
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    function sendMessage() {
        const text = messageInput.value.trim();
        
        if (text || filesToSend.length > 0) {
            // 这里应该是发送消息和文件的逻辑
            // 实际应用中，这里会调用API发送消息和上传文件
            
            // 示例：在界面上显示发送的消息和文件
            if (text) {
                // 显示文本消息
                addMessageToChat(text, true);
            }
            
            // 显示文件消息
            filesToSend.forEach(file => {
                if (file.type.startsWith('image/')) {
                    // 显示图片消息
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        addImageToChat(e.target.result, file.name, true);
                    };
                    reader.readAsDataURL(file);
                } else {
                    // 显示文件消息
                    addFileToChat(file.name, file.size, true);
                }
            });
            
            // 清空输入和预览
            messageInput.value = '';
            filesToSend = [];
            previewArea.innerHTML = '';
        }
    }
    
    // 图片预览功能
    function openImagePreview(src) {
        previewedImage.src = src;
        imagePreviewModal.style.display = 'flex';
    }
    
    closePreview.addEventListener('click', function() {
        imagePreviewModal.style.display = 'none';
    });
    
    imagePreviewModal.addEventListener('click', function(e) {
        if (e.target === imagePreviewModal) {
            imagePreviewModal.style.display = 'none';
        }
    });
    
    // 添加消息到聊天区域的函数
    function addMessageToChat(text, isSent) {
        // 实际应用中应该调用你的消息显示函数
        console.log('Message:', text, isSent);
    }
    
    function addImageToChat(src, filename, isSent) {
        // 实际应用中应该调用你的图片消息显示函数
        console.log('Image:', src, filename, isSent);
    }
    
    function addFileToChat(filename, size, isSent) {
        // 实际应用中应该调用你的文件消息显示函数
        console.log('File:', filename, size, isSent);
    }
});

// 在消息容器中显示文件/图片消息的函数
function displayFileMessage(fileData, isSent) {
    const messageContainer = document.getElementById('messageContainer');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isSent ? 'sent' : 'received'}`;
    
    if (!isSent) {
        // 对于接收的消息，显示发送者信息
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = fileData.sender || '未知用户';
        messageDiv.appendChild(senderDiv);
    }
    
    if (fileData.type === 'image') {
        // 图片消息
        const imgDiv = document.createElement('div');
        imgDiv.className = 'message-file';
        
        const img = document.createElement('img');
        img.src = fileData.url;
        img.alt = fileData.name;
        img.onclick = () => openImagePreview(fileData.url);
        
        imgDiv.appendChild(img);
        messageDiv.appendChild(imgDiv);
    } else {
        // 文件消息
        const fileDiv = document.createElement('div');
        fileDiv.className = 'file-message';
        
        const icon = document.createElement('div');
        icon.className = 'file-message-icon';
        icon.innerHTML = '<i class="fas fa-file"></i>';
        
        const infoDiv = document.createElement('div');
        infoDiv.className = 'file-message-info';
        
        const nameDiv = document.createElement('div');
        nameDiv.className = 'file-message-name';
        nameDiv.textContent = fileData.name;
        
        const sizeDiv = document.createElement('div');
        sizeDiv.className = 'file-message-size';
        sizeDiv.textContent = formatFileSize(fileData.size);
        
        infoDiv.appendChild(nameDiv);
        infoDiv.appendChild(sizeDiv);
        
        const downloadDiv = document.createElement('div');
        downloadDiv.className = 'file-download';
        downloadDiv.innerHTML = '<i class="fas fa-download"></i>';
        downloadDiv.onclick = () => downloadFile(fileData.url, fileData.name);
        
        fileDiv.appendChild(icon);
        fileDiv.appendChild(infoDiv);
        fileDiv.appendChild(downloadDiv);
        messageDiv.appendChild(fileDiv);
    }
    
    // 时间戳
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = formatTime(new Date());
    messageDiv.appendChild(timeDiv);
    
    messageContainer.appendChild(messageDiv);
    messageContainer.scrollTop = messageContainer.scrollHeight;
}

// 辅助函数
function formatTime(date) {
    return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function downloadFile(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}