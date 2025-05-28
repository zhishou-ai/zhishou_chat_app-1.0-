import sys
import asyncio
import websockets
import json
import sqlite3
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QFileDialog, QMessageBox

# 导入原有的窗口类
from nicheng import ChangeNicknameWindow
from jianqun import CreateGroupWindow


class DatabaseManager:
    def __init__(self, db_name='chat_app.db'):
        self.db_name = db_name
        self.initialize_database()

    def initialize_database(self):
        """初始化数据库表结构"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)

            # 创建消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    sender_id INTEGER NOT NULL,
                    sender_name TEXT NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    receiver_type TEXT NOT NULL,  -- 'private' or 'group'
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_sent INTEGER DEFAULT 0,  -- 0: received, 1: sent
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            # 创建群组表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    group_name TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            # 创建联系人表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER NOT NULL,
                    contact_name TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            conn.commit()
        except sqlite3.Error as e:
            print(f"数据库初始化错误: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def save_user(self, user_id, username, password):
        """保存用户信息"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO users (id, username, password) VALUES (?, ?, ?)",
                (user_id, username, password)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"保存用户错误: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def save_message(self, user_id, sender_id, sender_name, receiver_id, receiver_type, content, timestamp, is_sent=0):
        """保存消息到数据库"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO messages 
                (user_id, sender_id, sender_name, receiver_id, receiver_type, content, timestamp, is_sent) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, sender_id, sender_name, receiver_id, receiver_type, content, timestamp, is_sent)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"保存消息错误: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_messages(self, user_id, receiver_id, receiver_type, limit=50):
        """从数据库获取消息历史"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT sender_id, sender_name, content, timestamp, is_sent 
                FROM messages 
                WHERE user_id=? AND receiver_id=? AND receiver_type=?
                ORDER BY timestamp DESC LIMIT ?""",
                (user_id, receiver_id, receiver_type, limit)
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取消息错误: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def save_contact(self, user_id, contact_id, contact_name):
        """保存联系人"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO contacts (user_id, contact_id, contact_name) VALUES (?, ?, ?)",
                (user_id, contact_id, contact_name)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"保存联系人错误: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_contacts(self, user_id):
        """获取联系人列表"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT contact_id, contact_name FROM contacts WHERE user_id=?",
                (user_id,)
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取联系人错误: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def save_group(self, user_id, group_id, group_name):
        """保存群组信息"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO groups (user_id, group_id, group_name) VALUES (?, ?, ?)",
                (user_id, group_id, group_name)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"保存群组错误: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def get_groups(self, user_id):
        """获取群组列表"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT group_id, group_name FROM groups WHERE user_id=?",
                (user_id,)
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"获取群组错误: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()


class WebSocketClient(QThread, QObject):
    message_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self, username, password, action_type):
        QThread.__init__(self)
        QObject.__init__(self)
        self.username = username
        self.password = password
        self.action_type = action_type
        self.websocket = None
        self.running = False
        self.server_url = "ws://192.168.3.159:8765"
        self.loop = None
        self.user_id = None
        self._connected = False
        self.db_manager = DatabaseManager()

    def is_connected(self):
        return self._connected

    async def connect(self):
        print(f"尝试连接到 WebSocket 服务器: {self.server_url}")
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.server_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=1
                ),
                timeout=5.0
            )
            self._connected = True
            self.connection_changed.emit(True)

            login_msg = {
                "action": self.action_type,
                "username": self.username,
                "password": self.password
            }
            await self.websocket.send(json.dumps(login_msg))

            while self.running:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    self.message_received.emit(data)
                except websockets.exceptions.ConnectionClosed:
                    self._connected = False
                    self.connection_changed.emit(False)
                    break

        except Exception as e:
            print(f"连接错误: {e}")
            self._connected = False
            self.connection_changed.emit(False)
            # 模拟登录成功响应，以便可以查看本地数据
            # 只在离线模式下创建模拟用户ID
            self.message_received.emit({
                "action": f"{self.action_type}_response",
                "success": True,
                "user_id": -1,  # 离线模式使用负数ID
                "username": self.username
            })

    def send_message_sync(self, message: dict):
        if self.loop and self.running and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._send_message_async(message), self.loop)

    async def _send_message_async(self, message: dict):
        try:
            if self.websocket is None or self.websocket.closed:
                print("WebSocket 未连接，尝试重新连接...")
                await self.connect()

            if self.websocket and not self.websocket.closed:
                await self.websocket.send(json.dumps(message))
            else:
                print("无法发送消息：WebSocket 连接不可用")
        except Exception as e:
            print(f"发送消息失败: {e}")
            self._connected = False
            self.connection_changed.emit(False)

    async def disconnect(self):
        self.running = False
        if self.websocket:
            await self.websocket.close()
        self._connected = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.running = True
        self.loop.run_until_complete(self.connect())


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_zhi_liao()
        self.ui.setupUi(self)
        self.username = ""
        self.user_id = None
        self.db_manager = DatabaseManager()
        self.all_users = []  # 确保变量初始化

        # 显示登录对话框
        self.show_login_dialog()

    def show_login_dialog(self):
        """显示登录/注册对话框"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("登录/注册")
        dialog.setFixedSize(300, 200)

        layout = QtWidgets.QVBoxLayout()

        # 用户名输入
        username_input = QtWidgets.QLineEdit()
        username_input.setPlaceholderText("用户名")
        layout.addWidget(username_input)

        # 密码输入
        password_input = QtWidgets.QLineEdit()
        password_input.setPlaceholderText("密码")
        password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(password_input)

        # 按钮布局
        button_layout = QtWidgets.QHBoxLayout()

        # 登录按钮
        login_btn = QtWidgets.QPushButton("登录")
        login_btn.clicked.connect(lambda: self.handle_auth(
            "login",
            username_input.text(),
            password_input.text(),
            dialog
        ))
        button_layout.addWidget(login_btn)

        # 注册按钮
        register_btn = QtWidgets.QPushButton("注册")
        register_btn.clicked.connect(lambda: self.handle_auth(
            "register",
            username_input.text(),
            password_input.text(),
            dialog
        ))
        button_layout.addWidget(register_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # 非模态显示对话框
        dialog.exec()

    def handle_auth(self, action_type, username, password, dialog):
        """处理登录/注册"""
        username = username.strip()
        password = password.strip()

        if not username or not password:
            QtWidgets.QMessageBox.warning(dialog, "错误", "用户名和密码不能为空")
            return

        # 首先尝试从数据库获取用户ID
        try:
            conn = sqlite3.connect('chat_app.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username=?", (username,))
            result = cursor.fetchone()
            if result:
                self.user_id = result[0]
            else:
                # 新用户，使用临时ID
                self.user_id = -1
        except sqlite3.Error as e:
            print(f"获取用户ID错误: {e}")
            self.user_id = -1  # 出错时使用临时ID
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        # 初始化 websocket_client（每次登录/注册都新建一个连接）
        self.websocket_client = WebSocketClient(username, password, action_type)
        self.websocket_client.message_received.connect(self.handle_websocket_message)
        self.websocket_client.connection_changed.connect(self.handle_connection_change)
        self.websocket_client.start()

        # 关闭对话框
        dialog.accept()

        # 设置用户名
        self.username = username

        # 初始化界面
        self.online_users = []
        self.groups = {}
        self.current_chat = None
        self.chat_history = {}
        self.ui.pushButton_4.clicked.connect(self.open_nicheng_window)
        self.ui.pushButton_3.clicked.connect(self.open_jianqun_window)
        self.ui.pushButton.clicked.connect(self.open_file_dialog)
        self.ui.pushButton_2.clicked.connect(self.send_chat_message)
        self.ui.listWidget.itemClicked.connect(self.select_chat_target)

        # 安装事件过滤器用于回车发送消息
        self.ui.textEdit.installEventFilter(self)

        # 初始化用户列表（从本地数据库加载）
        self.init_user_list()
        self.setWindowTitle(f"知了聊天 - {username}")

        # 显示离线提示
        if not self.websocket_client.is_connected():
            self.display_message("系统", "当前处于离线模式，只能查看本地历史消息")
            # 离线模式下直接加载本地联系人
            self.load_local_contacts()
        else:
            self.display_message("系统", "正在连接服务器...")

    def load_local_contacts(self):
        """加载本地联系人"""
        if self.user_id is not None:
            # 加载联系人
            contacts = self.db_manager.get_contacts(self.user_id)
            for contact_id, contact_name in contacts:
                user_item = QtWidgets.QListWidgetItem(contact_name)
                user_item.setData(QtCore.Qt.ItemDataRole.UserRole, {
                    "username": contact_name,
                    "user_id": contact_id
                })
                self.ui.listWidget.addItem(user_item)

            # 加载群组
            groups = self.db_manager.get_groups(self.user_id)
            for group_id, group_name in groups:
                group_item = QtWidgets.QListWidgetItem(f"群:{group_name}")
                group_item.setData(QtCore.Qt.ItemDataRole.UserRole, f"群:{group_id}")
                self.ui.listWidget.addItem(group_item)

    def init_user_list(self):
        """初始化用户列表控件"""
        # 清除现有项
        self.ui.listWidget.clear()

        # 如果已登录，从数据库加载联系人和群组
        if self.user_id is not None:
            self.load_local_contacts()

    def update_user_list(self, users):
        """更新所有用户列表"""
        self.all_users = users

        # 保存当前选中的项
        current_item = self.ui.listWidget.currentItem()
        current_receiver = current_item.data(QtCore.Qt.ItemDataRole.UserRole) if current_item else None

        # 清除现有项
        self.ui.listWidget.clear()

        # 添加在线用户
        for user in users:
            if user["username"] != self.username:  # 不显示自己
                # 保存到数据库
                self.db_manager.save_contact(self.user_id, user["user_id"], user["username"])

                user_item = QtWidgets.QListWidgetItem(user["username"])
                # 存储user_id和username
                user_item.setData(QtCore.Qt.ItemDataRole.UserRole, {
                    "username": user["username"],
                    "user_id": user["user_id"]
                })
                self.ui.listWidget.addItem(user_item)

        # 添加群组
        groups = self.db_manager.get_groups(self.user_id)
        for group_id, group_name in groups:
            group_item = QtWidgets.QListWidgetItem(f"群:{group_name}")
            group_item.setData(QtCore.Qt.ItemDataRole.UserRole, f"群:{group_id}")
            self.ui.listWidget.addItem(group_item)

        # 恢复选中状态
        if current_receiver:
            for i in range(self.ui.listWidget.count()):
                item = self.ui.listWidget.item(i)
                if item.data(QtCore.Qt.ItemDataRole.UserRole) == current_receiver:
                    self.ui.listWidget.setCurrentItem(item)
                    break

    def update_group_list(self, groups):
        """更新群组列表"""
        self.groups = groups
        # 保存当前选中的项
        current_item = self.ui.listWidget.currentItem()
        current_receiver = current_item.data(QtCore.Qt.ItemDataRole.UserRole) if current_item else None

        # 清除现有项
        self.ui.listWidget.clear()

        # 添加在线用户
        for user in self.all_users:
            if user["username"] != self.username:
                # 保存到数据库
                self.db_manager.save_contact(self.user_id, user["user_id"], user["username"])

                user_item = QtWidgets.QListWidgetItem(user["username"])
                # 存储user_id和username
                user_item.setData(QtCore.Qt.ItemDataRole.UserRole, {
                    "username": user["username"],
                    "user_id": user["user_id"]
                })
                self.ui.listWidget.addItem(user_item)

        # 添加群组
        groups = self.db_manager.get_groups(self.user_id)
        for group_id, group_name in groups:
            group_item = QtWidgets.QListWidgetItem(f"群:{group_name}")
            group_item.setData(QtCore.Qt.ItemDataRole.UserRole, f"群:{group_id}")
            self.ui.listWidget.addItem(group_item)

        # 恢复选中状态
        if current_receiver:
            for i in range(self.ui.listWidget.count()):
                item = self.ui.listWidget.item(i)
                if item.data(QtCore.Qt.ItemDataRole.UserRole) == current_receiver:
                    self.ui.listWidget.setCurrentItem(item)
                    break



    def select_chat_target(self, item):
        """选择聊天对象"""
        if self.user_id is None:
            self.display_message("系统", "请先登录成功后再选择聊天对象")
            return

        receiver_data = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not receiver_data:
            return

        # 解析接收者数据
        if isinstance(receiver_data, dict):
            # 私聊
            self.current_chat = str(receiver_data["user_id"])  # 统一用user_id字符串
            self.current_chat_id = receiver_data["user_id"]
            self.current_chat_type = "private"
            self.ui.label.setText(f"私聊: {receiver_data['username']}")
            self.load_local_messages(receiver_data["user_id"], "private")
        elif isinstance(receiver_data, str) and receiver_data.startswith("群:"):
            # 群聊
            group_id = receiver_data[2:]
            self.current_chat = f"群:{group_id}"
            self.current_chat_id = group_id
            self.current_chat_type = "group"
            self.ui.label.setText(f"群聊: {group_id}")
            self.load_local_messages(group_id, "group")
        else:
            return

        # 更新聊天显示
        self.update_chat_display()

    def load_local_messages(self, receiver_id, receiver_type):
        """从本地数据库加载消息"""
        if self.user_id is None:
            return

        messages = self.db_manager.get_messages(self.user_id, receiver_id, receiver_type)

        # 确定接收者标识
        if receiver_type == "group":
            receiver = f"群:{receiver_id}"
        else:
            receiver = str(receiver_id)

        # 存储消息
        if receiver not in self.chat_history:
            self.chat_history[receiver] = []

        # 清空现有消息
        self.chat_history[receiver].clear()

        for msg in reversed(messages):
            sender_id, sender_name, content, timestamp, is_sent = msg
            converted_msg = {
                "sender": "我" if is_sent else sender_name,
                "content": content,
                "timestamp": timestamp,
                "is_group": receiver_type == "group"
            }
            self.chat_history[receiver].append(converted_msg)

    def request_group_history(self, group_id):
        """请求群组消息历史"""
        if self.user_id is None:
            self.display_message("系统", "请先登录成功后再获取历史消息")
            return

        if not self.websocket_client.is_connected():
            self.display_message("系统", "离线状态下无法获取最新历史消息")
            return

        message = {
            "action": "get_messages",
            "user_id": self.user_id,
            "receiver_type": "group",
            "receiver_id": group_id,
            "page": 1,
            "page_size": 50
        }
        self.websocket_client.send_message_sync(message)

    def request_private_history(self, user_id):
        """请求私聊消息历史"""
        if self.user_id is None:
            self.display_message("系统", "请先登录成功后再获取历史消息")
            return

        if not self.websocket_client.is_connected():
            self.display_message("系统", "离线状态下无法获取最新历史消息")
            return

        message = {
            "action": "get_messages",
            "user_id": self.user_id,
            "receiver_type": "private",
            "receiver_id": user_id,
            "page": 1,
            "page_size": 50
        }
        self.websocket_client.send_message_sync(message)

    def update_chat_display(self):
        """更新聊天显示区域"""
        if not self.current_chat:
            return
        if self.current_chat not in self.chat_history:
            self.chat_history[self.current_chat] = []
        chat_content = ""
        for msg in self.chat_history[self.current_chat]:
            sender = msg.get("sender", "未知")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            try:
                time_str = QtCore.QDateTime.fromString(timestamp[:19], QtCore.Qt.DateFormat.ISODate).toString(
                    "hh:mm:ss")
            except:
                time_str = ""
            if sender == "我":
                chat_content += f'<div style="text-align: right; margin: 5px;">'
                chat_content += f'<span style="color: #888; font-size: small;">{time_str}</span><br>'
                chat_content += f'<span style="background-color: #e3f2fd; padding: 5px 10px; border-radius: 10px; display: inline-block;">{content}</span>'
                chat_content += '</div>'
            else:
                chat_content += f'<div style="text-align: left; margin: 5px;">'
                chat_content += f'<span style="font-weight: bold; color: #333;">{sender}</span> '
                chat_content += f'<span style="color: #888; font-size: small;">{time_str}</span><br>'
                chat_content += f'<span style="background-color: #f1f1f1; padding: 5px 10px; border-radius: 10px; display: inline-block;">{content}</span>'
                chat_content += '</div>'
        self.ui.shu_chu.setHtml(chat_content)
        self.ui.shu_chu.verticalScrollBar().setValue(self.ui.shu_chu.verticalScrollBar().maximum())

    def handle_websocket_message(self, message):
        """处理从WebSocket接收到的消息"""
        action = message.get("action")

        if action == "message_history":
            # 处理消息历史
            receiver_type = message.get("receiver_type")
            receiver_id = message.get("receiver_id")
            messages = message.get("messages", [])

            # 确定接收者标识
            if receiver_type == "group":
                receiver = f"群:{receiver_id}"
            else:
                receiver = str(receiver_id)

            # 存储消息
            if receiver not in self.chat_history:
                self.chat_history[receiver] = []

            # 清空现有消息
            self.chat_history[receiver].clear()

            for msg in reversed(messages):
                # 转换消息格式
                sender_name = msg.get("sender_name")
                sender_id = msg.get("sender_id")
                content = msg.get("content")
                timestamp = msg.get("created_at", "")

                # 保存到本地数据库
                self.db_manager.save_message(
                    self.user_id,
                    sender_id,
                    sender_name,
                    receiver_id,
                    receiver_type,
                    content,
                    timestamp,
                    is_sent=(sender_id == self.user_id)
                )

                converted_msg = {
                    "sender": "我" if sender_id == self.user_id else sender_name,
                    "content": content,
                    "timestamp": timestamp,
                    "is_group": receiver_type == "group"
                }
                self.chat_history[receiver].append(converted_msg)

            # 如果当前正在查看这个聊天，则更新显示
            if self.current_chat == receiver:
                self.update_chat_display()

        elif action == "new_private_message":
            # 处理新私聊消息
            msg = message.get("message", {})
            sender_id = msg.get("sender_id")
            receiver_id = msg.get("receiver_id")
            content = msg.get("content")
            timestamp = msg.get("timestamp", "")
            sender_name = self.get_username_by_id(sender_id)

            if sender_id == self.user_id:
                receiver = str(receiver_id)
                sender_display = "我"
            else:
                receiver = str(sender_id)
                sender_display = sender_name

            if receiver not in self.chat_history:
                self.chat_history[receiver] = []

            # 保存到本地数据库
            self.db_manager.save_message(
                self.user_id,
                sender_id,
                sender_name,
                receiver_id,
                "private",
                content,
                timestamp,
                is_sent=(sender_id == self.user_id)
            )

            self.chat_history[receiver].append({
                "sender": sender_display,
                "content": content,
                "timestamp": timestamp,
                "is_group": False
            })

            if self.current_chat == receiver:
                self.update_chat_display()

        elif action == "new_group_message":
            # 处理新群聊消息
            group_id = message.get("group_id")
            msg = message.get("message", {})
            sender_id = msg.get("sender_id")
            content = msg.get("content")
            timestamp = msg.get("timestamp", "")
            sender_name = self.get_username_by_id(sender_id)

            receiver = f"群:{group_id}"
            sender_display = "我" if sender_id == self.user_id else sender_name

            if receiver not in self.chat_history:
                self.chat_history[receiver] = []

            # 保存到本地数据库
            self.db_manager.save_message(
                self.user_id,
                sender_id,
                sender_name,
                group_id,
                "group",
                content,
                timestamp,
                is_sent=(sender_id == self.user_id)
            )

            self.chat_history[receiver].append({
                "sender": sender_display,
                "content": content,
                "timestamp": timestamp,
                "is_group": True
            })

            if self.current_chat == receiver:
                self.update_chat_display()

        elif action == "error":
            # 显示错误消息
            error_msg = message.get("message", "未知错误")
            self.display_message("系统", f"错误: {error_msg}")

        elif action == "online_users":
            # 服务器推送的在线用户列表
            users = message.get("users", [])
            self.update_user_list(users)

        elif action == "group_list":
            groups = message.get("groups", [])
            self.update_group_list(groups)

        elif action == "group_created":
            group_name = message.get("group_name")
            group_id = message.get("group_id")
            self.display_message("系统", f"群组 '{group_name}' 创建成功！")

        elif action == "added_to_group":
            group_name = message.get("group_name")
            group_id = message.get("group_id")
            self.display_message("系统", f"已被添加到群组 '{group_name}'！")

        elif action == "login_response":
            success = message.get("success")
            if success:
                self.user_id = message.get("user_id")
                self.username = message.get("username")

                # 保存用户信息到本地数据库
                self.db_manager.save_user(self.user_id, self.username, "")

                self.ui.listWidget.setEnabled(True)
                self.ui.pushButton_2.setEnabled(True)

                if self.websocket_client.is_connected():
                    self.display_message("系统", "登录成功！")
                else:
                    self.display_message("系统", "离线登录成功！")

                # 初始化用户列表
                self.init_user_list()

                # 如果在线，主动请求在线用户列表
                if self.websocket_client.is_connected():
                    self.websocket_client.send_message_sync({
                        "action": "get_online_users"
                    })
            else:
                self.display_message("系统", f"登录失败：{message.get('message', '未知错误')}")

        elif action == "register_response":
            if message.get("success"):
                self.user_id = message.get("user_id")
                self.username = message.get("username")

                # 保存用户信息到本地数据库
                self.db_manager.save_user(self.user_id, self.username, "")

                self.ui.listWidget.setEnabled(True)
                self.ui.pushButton_2.setEnabled(True)
                self.display_message("系统", "注册成功！")

                # 初始化用户列表
                self.init_user_list()

                # 主动请求在线用户列表
                self.websocket_client.send_message_sync({
                    "action": "get_online_users"
                })
            else:
                self.display_message("系统", f"注册失败：{message.get('message', '未知错误')}")

        elif action == "all_users":
            users = message.get("users", [])
            self.update_user_list(users)

    def handle_connection_change(self, connected):
        """处理连接状态变化"""
        if connected:
            self.display_message("系统", "已连接到聊天服务器")
        else:
            self.display_message("系统", "与聊天服务器的连接已断开")

    def display_message(self, sender, content):
        """在聊天区域显示消息"""
        current_text = self.ui.shu_chu.toHtml()
        new_text = f"{sender}: {content}<br>{current_text}"
        self.ui.shu_chu.setHtml(new_text)
        self.ui.shu_chu.verticalScrollBar().setValue(self.ui.shu_chu.verticalScrollBar().maximum())

    def send_chat_message(self):
        """发送聊天消息"""
        if self.user_id is None:
            self.display_message("系统", "请先登录成功后再发送消息")
            return

        text = self.ui.textEdit.toPlainText().strip()
        if not text:
            return

        if not self.current_chat:
            self.display_message("系统", "请选择聊天对象")
            return

        is_group = self.current_chat.startswith("群:")
        receiver_id = self.current_chat_id
        receiver_type = "group" if is_group else "private"

        # 保存到本地数据库（标记为已发送）
        timestamp = QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.DateFormat.ISODate)
        self.db_manager.save_message(
            self.user_id,
            self.user_id,
            self.username,
            receiver_id,
            receiver_type,
            text,
            timestamp,
            is_sent=1
        )

        # 添加到聊天历史
        if self.current_chat not in self.chat_history:
            self.chat_history[self.current_chat] = []

        self.chat_history[self.current_chat].append({
            "sender": "我",
            "content": text,
            "timestamp": timestamp,
            "is_group": is_group
        })

        # 更新显示
        self.update_chat_display()

        # 如果在线，通过网络发送
        if self.websocket_client.is_connected():
            message = {
                "action": "send_message",
                "sender_id": self.user_id,
                "receiver_type": receiver_type,
                "receiver_id": receiver_id,
                "content": text
            }
            try:
                self.websocket_client.send_message_sync(message)
                self.ui.textEdit.clear()
            except Exception as e:
                self.display_message("系统", f"发送消息失败: {str(e)}")
        else:
            self.display_message("系统", "离线状态下消息已保存到本地")
            self.ui.textEdit.clear()

    def open_nicheng_window(self):
        """打开昵称设置窗口"""
        self.nicheng_window = ChangeNicknameWindow()
        self.nicheng_window.show()

        # 连接昵称更改信号
        if hasattr(self.nicheng_window, 'nickname_changed'):
            self.nicheng_window.nickname_changed.connect(self.update_nickname)

    def update_nickname(self, new_nickname):
        """更新昵称"""
        message = {
            "action": "update_nickname",
            "username": self.username,
            "nickname": new_nickname
        }
        # 通过WebSocket发送（使用同步方法）
        self.websocket_client.send_message_sync(message)

    def open_jianqun_window(self):
        """打开建群窗口"""
        # 如果离线，使用本地联系人
        if not self.websocket_client.is_connected():
            contacts = self.db_manager.get_contacts(self.user_id) if self.user_id else []
            usernames = [contact[1] for contact in contacts]
        else:
            # 用所有用户列表
            usernames = [user["username"] for user in self.all_users if "username" in user]

        self.jianqun_window = CreateGroupWindow(usernames)
        self.jianqun_window.show()

        # 连接建群信号
        if hasattr(self.jianqun_window, 'group_created'):
            self.jianqun_window.group_created.connect(self.create_group)

    def create_group(self, group_name, members):
        """创建新群组"""
        # members 是用户名列表，需要转成 user_id 列表
        user_ids = []

        # 如果在线，使用服务器用户列表
        if self.websocket_client.is_connected():
            for username in members:
                for user in self.all_users:
                    if user["username"] == username:
                        user_ids.append(user["user_id"])
                        break
        else:
            # 如果离线，使用本地数据库
            if self.user_id:
                contacts = self.db_manager.get_contacts(self.user_id)
                username_to_id = {name: id for id, name in contacts}
                for username in members:
                    if username in username_to_id:
                        user_ids.append(username_to_id[username])

        # 把自己也加进去（如果没选自己）
        if self.user_id not in user_ids:
            user_ids.append(self.user_id)

        # 如果在线，发送建群请求
        if self.websocket_client.is_connected():
            message = {
                "action": "create_group",
                "group_name": group_name,
                "creator_id": self.user_id,
                "initial_members": user_ids
            }
            self.websocket_client.send_message_sync(message)
        else:
            self.display_message("系统", "离线状态下无法创建新群组")

    def open_file_dialog(self):
        """打开文件选择对话框"""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("选择文件")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                print("选择的文件:", selected_files[0])
                # 这里可以添加文件发送逻辑

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 断开WebSocket连接
        if hasattr(self, 'websocket_client') and self.websocket_client.isRunning():
            self.websocket_client.running = False
            self.websocket_client.quit()
            self.websocket_client.wait()
        event.accept()

    def eventFilter(self, obj, event):
        # 回车发送消息
        if obj == self.ui.textEdit and event.type() == QtCore.QEvent.Type.KeyPress:
            if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
                if not (event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier):
                    self.send_chat_message()
                    return True  # 阻止回车换行
        return super().eventFilter(obj, event)

    def get_username_by_id(self, user_id):
        # 先从在线用户中查找
        for user in getattr(self, "all_users", []):
            if user.get("user_id") == user_id:
                return user.get("username")

        # 如果是离线模式或未找到，从本地数据库查找
        if self.user_id is not None:
            contacts = self.db_manager.get_contacts(self.user_id)
            for contact_id, contact_name in contacts:
                if contact_id == user_id:
                    return contact_name

        return f"用户{user_id}"


class Ui_zhi_liao(object):
    def setupUi(self, zhi_liao):
        zhi_liao.setObjectName("zhi_liao")
        zhi_liao.resize(1200, 710)
        self.bei_jing = QtWidgets.QLabel(parent=zhi_liao)
        self.bei_jing.setGeometry(QtCore.QRect(0, -40, 1150, 751))
        self.bei_jing.setText("")
        self.bei_jing.setPixmap(QtGui.QPixmap("D:\图片\ (23).png"))
        self.bei_jing.setScaledContents(True)
        self.bei_jing.setObjectName("bei_jing")
        self.shu_chu = QtWidgets.QTextBrowser(parent=zhi_liao)
        self.shu_chu.setGeometry(QtCore.QRect(330, 50, 801, 471))
        self.shu_chu.setStyleSheet("QTextBrowser {\n"
                                   "    background-color: rgba(0, 0, 0, 20);\n"
                                   "    color: black;\n"
                                   "    border-radius: 10px;\n"
                                   "    padding: 20px;\n"
                                   "    border: none;\n"
                                   "}\n"
                                   "")
        self.shu_chu.setText("")
        self.shu_chu.setObjectName("shu_chu")
        self.pushButton = QtWidgets.QPushButton(parent=zhi_liao)
        self.pushButton.setGeometry(QtCore.QRect(1030, 610, 61, 91))
        self.pushButton.setStyleSheet("QPushButton {\n"
                                      "    background-color: transparent;\n"
                                      "    padding: 15px 20px 5px 20px;\n"
                                      "    color: black;\n"
                                      "    padding: 5px 10px;\n"
                                      "    font-family: \"Microsoft YaHei\";\n"
                                      "    font-size: 14px;\n"
                                      "    border-radius: 4px;\n"
                                      "    border: 1px solid rgba(0, 0, 0, 10%);\
                                      }")
        self.pushButton.setObjectName("pushButton")
        self.textEdit = QtWidgets.QTextEdit(parent=zhi_liao)
        self.textEdit.setGeometry(QtCore.QRect(300, 600, 711, 111))
        self.textEdit.setStyleSheet("QLineEdit, QTextEdit {\n"
                                    "    border: 2px solid #CCCCCC;\n"
                                    "    border-radius: 10px;\n"
                                    "    padding: 20px;\n"
                                    "    background-color: rgba(0, 0, 0, 30);\n"
                                    "    border: none;\n"
                                    "    color: white;\n"
                                    "    font-family: \"宋体\";\n"
                                    "    font-size: 18px;\n"
                                    "    font-weight: bold;\n"
                                    "}\n"
                                    "")
        self.textEdit.setObjectName("textEdit")
        self.pushButton_2 = QtWidgets.QPushButton(parent=zhi_liao)
        self.pushButton_2.setGeometry(QtCore.QRect(930, 600, 81, 111))
        self.pushButton_2.setStyleSheet("QPushButton {\n"
                                        "    background-color: transparent;\n"
                                        "    border: none;\n"
                                        "    color: black;\n"
                                        "    padding: 18px 20px 5px 20px;\n"
                                        "    font-family: \"Microsoft YaHei\";\n"
                                        "    font-size: 16px;\n"
                                        "}\n"
                                        "QPushButton:hover {\n"
                                        "    background-color: transparent;\n"
                                        "}\n"
                                        "QPushButton:pressed {\n"
                                        "    color: rgba(0, 0, 0, 150);\n"
                                        "}\n"
                                        "QPushButton:disabled {\n"
                                        "    color: rgba(0, 0, 0, 50);\n"
                                        "}")
        self.pushButton_2.setObjectName("pushButton_2")
        self.listWidget = QtWidgets.QListWidget(parent=zhi_liao)
        self.listWidget.setGeometry(QtCore.QRect(0, 0, 261, 741))
        self.listWidget.setStyleSheet("QListWidget {\n"
                                      "    outline: 0;\n"
                                      "    border: 2px solid rgba(0, 0, 0, 30%);\n"
                                      "    background-color: rgba(0, 0, 0, 0);\n"
                                      "    border-radius: 0px;\n"
                                      "    padding: 1px;\n"
                                      "}\n"
                                      "QListWidget::item {\n"
                                      "    height: 50px;\n"
                                      "    padding: 0 15px;\n"
                                      "    border: none;\n"
                                      "    border-radius: 0;\n"
                                      "    margin: 0;\n"
                                      "    background-color: rgba(50, 50, 50, 70);\n"
                                      "    color: white;\n"
                                      "    font-family: \"宋体\";\n"
                                      "    font-size: 18px;\n"
                                      "    font-weight: bold;\n"
                                      "    border-bottom: 2px solid rgba(30, 30, 30, 90);\n"
                                      "}\n"
                                      "QListWidget::item:first {\n"
                                      "    border-top-left-radius: 0px;\n"
                                      "    border-top-right-radius: 0px;\n"
                                      "}\n"
                                      "QListWidget::item:last {\n"
                                      "    border-bottom-left-radius: 10px;\n"
                                      "    border-bottom-right-radius: 10px;\n"
                                      "    border-bottom: none;\n"
                                      "}\n"
                                      "QListWidget::item:hover {\n"
                                      "    background-color: rgba(70, 70, 70, 100);\n"
                                      "    border-bottom-color: rgba(50, 50, 50, 120);\n"
                                      "}\n"
                                      "QListWidget::item:selected {\n"
                                      "    background-color: rgba(90, 90, 90, 150);\n"
                                      "    border-bottom-color: rgba(70, 70, 70, 170);\n"
                                      "    color: white;\n"
                                      "}\n"
                                      "QScrollBar:vertical {\n"
                                      "    background: rgba(0, 0, 0, 0);\n"
                                      "    width: 12px;\n"
                                      "    margin: 10px 0;\n"
                                      "    border: none;\n"
                                      "}\n"
                                      "QScrollBar::handle:vertical {\n"
                                      "    background: rgba(150, 150, 150, 60);\n"
                                      "    border-radius: 6px;\n"
                                      "    min-height: 30px;\n"
                                      "    margin: 2px;\n"
                                      "    border: none;\n"
                                      "}\n"
                                      "QScrollBar::handle:vertical:hover {\n"
                                      "    background: rgba(180, 180, 180, 60);\n"
                                      "}\n"
                                      "QScrollBar::add-page:vertical,\n"
                                      "QScrollBar::sub-page:vertical,\n"
                                      "QScrollBar::sub-page:vertical,\n"
                                      "QScrollBar::up-arrow:vertical,\n"
                                      "QScrollBar::down-arrow:vertical {\n"
                                      "    background: transparent;\n"
                                      "}\n"
                                      "QListWidget::item::icon {\n"
                                      "    margin-left: 10px;\n"
                                      "    margin-right: 15px;\n"
                                      "}")
        self.listWidget.setObjectName("listWidget")
        item = QtWidgets.QListWidgetItem()
        self.listWidget.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.listWidget.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.listWidget.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.listWidget.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.listWidget.addItem(item)

        # 原"建群"按钮
        self.pushButton_3 = QtWidgets.QPushButton(parent=zhi_liao)
        self.pushButton_3.setGeometry(QtCore.QRect(1040, 10, 61, 41))
        self.pushButton_3.setStyleSheet("QPushButton {\n"
                                        "    background-color: transparent;\n"
                                        "    padding: 15px 20px 5px 20px;\n"
                                        "    color: black;\n"
                                        "    padding: 5px 10px;\n"
                                        "    font-family: \"Microsoft YaHei\";\n"
                                        "    font-size: 14px;\n"
                                        "    border-radius: 4px;\n"
                                        "    border: 1px solid rgba(0, 0, 0, 20%);\n"
                                        "}\n"
                                        "QPushButton:hover {\n"
                                        "    background-color: transparent;\n"
                                        "    border: 1px solid rgba(0, 0, 0, 20%);\n"
                                        "}\n"
                                        "QPushButton:pressed {\n"
                                        "    background-color: rgba(0, 0, 0, 20%);\n"
                                        "    border: 1px solid rgba(0, 0, 0, 30%);\n"
                                        "    color: black;\n"
                                        "}\n"
                                        "QPushButton:disabled {\n"
                                        "    color: rgba(0, 0, 0, 30%);\n"
                                        "    border: 1px solid rgba(0, 0, 0, 5%);\n"
                                        "}")
        self.pushButton_3.setObjectName("pushButton_3")

        # 新添加的按钮（在"建群"按钮左侧5px处）
        self.pushButton_4 = QtWidgets.QPushButton(parent=zhi_liao)
        self.pushButton_4.setGeometry(QtCore.QRect(974, 10, 61, 41))  # 1040-61-5=974
        self.pushButton_4.setStyleSheet("QPushButton {\n"
                                        "    background-color: transparent;\n"
                                        "    padding: 15px 20px 5px 20px;\n"
                                        "    color: black;\n"
                                        "    padding: 5px 10px;\n"
                                        "    font-family: \"Microsoft YaHei\";\n"
                                        "    font-size: 14px;\n"
                                        "    border-radius: 4px;\n"
                                        "    border: 1px solid rgba(0, 0, 0, 20%);\n"
                                        "}\n"
                                        "QPushButton:hover {\n"
                                        "    background-color: transparent;\n"
                                        "    border: 1px solid rgba(0, 0, 0, 20%);\n"
                                        "}\n"
                                        "QPushButton:pressed {\n"
                                        "    background-color: rgba(0, 0, 0, 20%);\n"
                                        "    border: 1px solid rgba(0, 0, 0, 30%);\n"
                                        "    color: black;\n"
                                        "}\n"
                                        "QPushButton:disabled {\n"
                                        "    color: rgba(0, 0, 0, 30%);\n"
                                        "    border: 1px solid rgba(0, 0, 0, 5%);\n"
                                        "}")
        self.pushButton_4.setObjectName("pushButton_4")

        self.label = QtWidgets.QLabel(parent=zhi_liao)
        self.label.setGeometry(QtCore.QRect(260, 10, 131, 41))
        self.label.setStyleSheet("QLabel{\n"
                                 "    background-color: transparent;\n"
                                 "    padding: 3px 20px 3px 20px;\n"
                                 "    color: black;\n"
                                 "}")
        self.label.setObjectName("label")

        self.retranslateUi(zhi_liao)
        QtCore.QMetaObject.connectSlotsByName(zhi_liao)

    def retranslateUi(self, zhi_liao):
        _translate = QtCore.QCoreApplication.translate
        zhi_liao.setWindowTitle(_translate("zhi_liao", "知了聊天"))
        self.pushButton.setText(_translate("zhi_liao", "文件"))
        self.pushButton_2.setText(_translate("zhi_liao", "发送"))
        __sortingEnabled = self.listWidget.isSortingEnabled()
        self.listWidget.setSortingEnabled(False)
        item = self.listWidget.item(0)
        item.setText(_translate("zhi_liao", "伪按钮1"))
        item = self.listWidget.item(1)
        item.setText(_translate("zhi_liao", "伪按钮2"))
        item = self.listWidget.item(2)
        item.setText(_translate("zhi_liao", "伪按钮3"))
        item = self.listWidget.item(3)
        item.setText(_translate("zhi_liao", "伪按钮4"))
        item = self.listWidget.item(4)
        item.setText(_translate("zhi_liao", "伪按钮5"))
        self.listWidget.setSortingEnabled(__sortingEnabled)
        self.pushButton_3.setText(_translate("zhi_liao", "建群"))
        self.pushButton_4.setText(_translate("zhi_liao", "设置"))  # 为新按钮设置文本
        self.label.setText(_translate("zhi_liao", "群聊、好友名"))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()  # 确保显示主窗口
    sys.exit(app.exec())