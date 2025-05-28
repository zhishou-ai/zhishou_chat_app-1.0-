import asyncio
import websockets
import json
import time
import datetime
import logging
from sql_program import DatabaseManager, AuthService, FriendService, GroupService, MessageService
from typing import Dict, List, Set, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatServer:
    def __init__(self):
        self.db = DatabaseManager()
        self.auth = AuthService(self.db)
        self.friend_service = FriendService(self.db)
        self.group_service = GroupService(self.db)
        self.message_service = MessageService()
        
        # 在线用户字典: {user_id: websocket}
        self.online_users: Dict[int, websockets.WebSocketServerProtocol] = {}
        # 用户订阅的群组: {user_id: set(group_ids)}
        self.user_subscriptions: Dict[int, Set[int]] = {}

    @staticmethod
    def json_serial(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
        
    


    async def broadcast_all_users(self):
        """向所有在线用户，发送所有用户列表"""
        online_user_ids = list(self.online_users.keys())
        users = []
        user = self.db.execute_query("SELECT user_id, username FROM users")
        if user:
            for uid in user:
                users.append({"user_id": uid["user_id"], "username": uid["username"]})
        data = {
            "action": "all_users",
            "users": users
        }
        for uid in online_user_ids:
            await self.send_to_user(uid, data)


    async def handle_connection(self, websocket):
        logger.info(f"新客户端连接: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get("action")
                    if action == "login":
                        await self.handle_login(websocket, data)
                    elif action == "register":
                        await self.handle_register(websocket, data)
                    elif action == "web_online":
                        await self.web_online(websocket, data)
                    elif action == "send_message":
                        await self.handle_send_message(websocket, data)
                    elif action == "get_messages":
                        await self.handle_get_messages(websocket, data)
                    # 你可以继续补充其它 action
                    elif action == "create_group":
                        await self.handle_create_group(websocket, data)
                    elif action == "update_nickname":
                        await self.handle_update_nickname(websocket,data)
                    elif action == "logout":
                        await self.handle_disconnect(websocket)
                        return
                    else:
                        await self.send_error(websocket, "未知操作")
                except Exception as e:
                    logger.error(f"消息处理异常: {e}", exc_info=True)
                    await self.send_error(websocket, "服务器内部错误")
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"客户端正常断开: {websocket.remote_address}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"客户端异常断开: {websocket.remote_address}, 原因: {e}")
        except Exception as e:
            logger.error(f"连接处理异常: {type(e).__name__}: {e}", exc_info=True)
        finally:
            await self.handle_disconnect(websocket)
            logger.info(f"连接清理完成: {websocket.remote_address}")

    async def send_error(self, websocket, message: str):
        """发送错误消息的通用方法"""
        await websocket.send(json.dumps({
            'action': 'error',
            'message': message
        }))

    async def handle_register(self, websocket, data):
        """处理用户注册请求"""
        try:
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            if not username or not password:
                await self.send_error(websocket, '用户名和密码不能为空')
                return

            # 调用AuthService进行注册
            result = self.auth.register_user(username, password)
            
            response = {
                'action': 'register_response',
                'success': result['success'],
                'message': result.get('message', '注册成功' if result['success'] else '注册失败'),
            }
            
            if result['success']:
                user_id = result.get('user_id')
                response['user_id'] = user_id  
                self.online_users[user_id] = websocket


            else:
                response['error'] = result.get('error', '注册失败')
            
            await websocket.send(json.dumps(response))
            await self.broadcast_all_users()
            await self.send_group_list(user_id)

        except Exception as e:
            logger.error(f"注册处理出错: {e}", exc_info=True)
            await self.send_error(websocket, '注册过程中发生错误')

    async def handle_login(self, websocket, data):
        """处理用户登录请求"""
        try:
            username = data.get('username')
            password = data.get('password', '').strip()
            if not username or not password:
                await self.send_error(websocket, '用户名和密码不能为空')
                return

            # 调用 AuthService 进行校验
            auth_result = self.auth.login_user(username, password)
            if not auth_result['success']:
                await self.send_error(websocket, auth_result.get('error', '登录失败'))
                return


            user_id = auth_result['user_id']
            if user_id in self.online_users:
                await self.send_error(websocket, '该用户已在线')
                return

            # 登录成功
            self.online_users[user_id] = websocket
            logger.info(f"User {user_id} logged in")
            await self.broadcast_all_users()

            # 发送离线消息
            await self.send_offline_messages(user_id)

            # 发送登录成功响应
            response = {
                'action': 'login_response',
                'success': True,
                'user_id': user_id,
                'username': auth_result.get('username')
            }
            await self.send_to_user(user_id, response)

            # 发送好友和群组列表
            await self.send_friend_list(user_id)
            await self.send_group_list(user_id)
            await self.broadcast_all_users()
        except Exception as e:
            logger.error(f"登录处理出错: {e}", exc_info=True)
            await self.send_error(websocket, '登录过程中发生错误')
    
    async def web_online(self, websocket, data):
        user_id = data.get('user_id')
        if not user_id:
            logger.error("web_online 缺少 user_id")
            return
        self.online_users[user_id] = websocket


    
    async def send_friend_list(self, user_id):
        """发送好友列表给用户"""
        try:
            friends = self.friend_service.get_friends(user_id)
            if friends['success']:
                response = {
                    'action': 'friend_list',
                    'friends': friends['friends']
                }
                await self.send_to_user(user_id, response)
        except Exception as e:
            logger.error(f"发送好友列表出错: {e}", exc_info=True)
    
    async def send_group_list(self, user_id):
        """发送群组列表给用户"""
        try:
            groups = self.group_service.get_user_groups(user_id)
            if groups['success']:
                response = {
                    'action': 'group_list',
                    'groups': groups['groups']
                }
                await self.send_to_user(user_id, response)
        except Exception as e:
            logger.error(f"发送群组列表出错: {e}", exc_info=True)
    
    async def handle_disconnect(self, websocket):
        """处理客户端断开连接"""
        try:
            for user_id, ws in list(self.online_users.items()):
                if ws == websocket:
                    self.online_users.pop(user_id, None)
                    self.user_subscriptions.pop(user_id, None)
                    logger.info(f"User {user_id} disconnected")
                    await self.notify_friends_status(user_id, False)
                    await self.broadcast_all_users()
                    break
        except Exception as e:
            logger.error(f"断开连接处理出错: {e}", exc_info=True)

    async def notify_friends_status(self, user_id: int, is_online: bool):
        """通知好友用户上线/下线状态"""
        try:
            friends = self.friend_service.get_friends(user_id)
            if friends['success']:
                for friend in friends['friends']:
                    friend_id = friend['user_id']
                    if friend_id in self.online_users:
                        await self.send_to_user(friend_id, {
                            'action': 'friend_status',
                            'friend_id': user_id,
                            'is_online': is_online
                        })
        except Exception as e:
            logger.error(f"通知好友状态出错: {e}", exc_info=True)

    async def send_to_user(self, user_id: int, data: dict):
        """安全地向用户发送消息"""
        try:
            ws = self.online_users.get(user_id)
            if ws and not ws.closed:
                await ws.send(json.dumps(data, default=self.json_serial))
            else:
                logger.warning(f"用户 {user_id} 的连接不存在或已关闭")
                # 如果连接已关闭，从在线用户中移除
                if user_id in self.online_users:
                    self.online_users.pop(user_id, None)
                    self.user_subscriptions.pop(user_id, None)
                    # 通知好友用户下线
                    await self.notify_friends_status(user_id, False)
        except Exception as e:
            logger.error(f"向用户 {user_id} 发送消息失败: {e}")
            # 如果发送失败，认为连接已断开
            if user_id in self.online_users:
                self.online_users.pop(user_id, None)
                self.user_subscriptions.pop(user_id, None)
                await self.notify_friends_status(user_id, False)

    async def send_offline_messages(self, user_id):
        """发送离线时收到的消息"""
        try:
            # 获取私聊消息
            private_messages = self.message_service.get_messages(
                user_id, "private", user_id, 1, 100
            )
            
            # 获取群聊消息
            groups = self.group_service.get_user_groups(user_id)
            if groups['success']:
                for group in groups['groups']:
                    group_messages = self.message_service.get_messages(
                        user_id, "group", group['group_id'], 1, 100
                    )
                    if group_messages['success']:
                        response = {
                            'action': 'group_messages',
                            'group_id': group['group_id'],
                            'messages': group_messages['messages']
                        }
                        await self.send_to_user(user_id, response)
            
            if private_messages['success']:
                response = {
                    'action': 'private_messages',
                    'messages': private_messages['messages']
                }
                await self.send_to_user(user_id, response)
        except Exception as e:
            logger.error(f"发送离线消息出错: {e}", exc_info=True)
    
    async def handle_get_friends(self, websocket, data):
        """处理获取好友列表请求"""
        try:
            user_id = data.get('user_id')
            if not user_id:
                await self.send_error(websocket, '缺少用户ID')
                return
                
            friends = self.friend_service.get_friends(user_id)
            if friends['success']:
                response = {
                    'action': 'friend_list',
                    'friends': friends['friends']
                }
                await self.send_to_user(user_id, response)
        except Exception as e:
            logger.error(f"获取好友列表出错: {e}", exc_info=True)
            await self.send_error(websocket, '获取好友列表失败')
    
    async def handle_get_groups(self, websocket, data):
        """处理获取群组列表请求"""
        try:
            user_id = data.get('user_id')
            if not user_id:
                await self.send_error(websocket, '缺少用户ID')
                return
                
            groups = self.group_service.get_user_groups(user_id)
            if groups['success']:
                response = {
                    'action': 'group_list',
                    'groups': groups['groups']
                }
                await self.send_to_user(user_id, response)
        except Exception as e:
            logger.error(f"获取群组列表出错: {e}", exc_info=True)
            await self.send_error(websocket, '获取群组列表失败')
    
    async def handle_get_messages(self, websocket, data):
        """处理获取消息历史请求"""
        try:
            user_id = int(data.get('user_id'))
        except (TypeError, ValueError):
            user_id = None
        try:
            receiver_id = int(data.get('receiver_id')) if data.get('receiver_id') is not None else None
            sender_id = int(data.get('sender_id')) if data.get('sender_id') is not None else None
            
            user_id = data.get('user_id')
            receiver_type = data.get('receiver_type')
            receiver_id = data.get('receiver_id')
            page = data.get('page', 1)
            page_size = data.get('page_size', 20)
            
            if not user_id or not receiver_type or not receiver_id:
                await self.send_error(websocket, '缺少必要参数')
                return
                
            messages = self.message_service.get_messages(
                user_id, receiver_type, receiver_id, page, page_size
            )
            if messages['success']:
                # 获取发送者昵称
                sender_names = {}
                for msg in messages['messages']:
                    if msg['sender_id'] not in sender_names:
                        user = self.db.execute_query(
                            "SELECT username FROM users WHERE user_id = %s",
                            (msg['sender_id'],)
                        )
                        sender_names[msg['sender_id']] = user[0]['username'] if user else "未知用户"
                # 添加发送者昵称到消息中
                enriched_messages = []
                for msg in messages['messages']:
                    enriched_msg = dict(msg)
                    enriched_msg['sender_name'] = sender_names.get(msg['sender_id'], "未知用户")
                    enriched_messages.append(enriched_msg)
                
                response = {
                    'action': 'message_history',
                    'receiver_type': receiver_type,
                    'receiver_id': receiver_id,
                    'messages': enriched_messages
                }
                await self.send_to_user(user_id, response)
            else:
                await self.send_error(websocket, messages.get('error', '获取消息历史失败'))
        except Exception as e:
            logger.error(f"获取消息历史出错: {e}", exc_info=True)
            await self.send_error(websocket, '获取消息历史失败')

    async def handle_send_message(self, websocket, data):
        """处理发送消息请求"""
        try:
            sender_id = int(data.get('sender_id')) if data.get('sender_id') is not None else None
            receiver_id = int(data.get('receiver_id')) if data.get('receiver_id') is not None else None
            receiver_type = data.get('receiver_type')
            content = data.get('content', '').strip()

            # 验证输入
            if not sender_id or not receiver_type or not receiver_id:
                await self.send_error(websocket, '缺少必要参数')
                return
                
            if not content:
                await self.send_error(websocket, '消息内容不能为空')
                return

            # 保存消息到数据库
            result = self.message_service.send_message(
                sender_id, receiver_type, receiver_id, content
            )

            if not result['success']:
                await self.send_error(websocket, result.get('error', '发送消息失败'))
                return

            # 获取发送者昵称
            sender_name = None
            try:
                user = self.db.execute_query("SELECT username FROM users WHERE user_id = %s", (sender_id,))
                if user and len(user) > 0:
                    sender_name = user[0]['username']
            except Exception as e:
                logger.error(f"获取用户信息出错: {e}")
                sender_name = None

            message = {
                'message_id': result['msg_id'],
                'sender_id': sender_id,
                'receiver_type': receiver_type,
                'receiver_id': receiver_id,
                'content': content,
                'sender_name': sender_name,
                'timestamp': datetime.datetime.now().isoformat()
            }

            if receiver_type == 'private':
                await self.handle_private_message(sender_id, message)
            elif receiver_type == 'group':
                await self.handle_group_message(sender_id, message)
            else:
                await self.send_error(websocket, '无效的接收者类型')
        except Exception as e:
            logger.error(f"发送消息处理出错: {e}", exc_info=True)
            await self.send_error(websocket, '发送消息失败')

    async def handle_private_message(self, sender_id: int, message: dict):
        """处理私聊消息"""
        try:
            receiver_id = message['receiver_id']
            
            # 发送给发送方的消息（显示为 sent）
            response_to_sender = {
                'action': 'new_private_message',
                'message': {
                    'message_id': message['message_id'],
                    'sender_id': sender_id,
                    'receiver_id': receiver_id,
                    'content': message['content'],
                    'direction': 'sent'  # 添加方向标识
                }
            }
            # 发送给接收方的消息（显示为 received）
            response_to_receiver = {
                'action': 'new_private_message',
                'message': {
                    'message_id': message['message_id'],
                    'sender_id': sender_id,
                    'receiver_id': receiver_id,
                    'content': message['content'],
                    'direction': 'received'  # 添加方向标识
                }
            }
            # 分别发送
            await self.send_to_user(sender_id, response_to_sender)
            print(f"在线用户：{self.online_users}")
            if receiver_id in self.online_users:
                await self.send_to_user(receiver_id, response_to_receiver)
        except Exception as e:
            logger.error(f"处理私聊消息出错: {e}", exc_info=True)
    
    async def handle_group_message(self, sender_id: int, message: dict):
        """处理群聊消息"""
        try:
            group_id = message['receiver_id']
            
            # 获取群成员
            members = self.db.execute_query(
                "SELECT user_id FROM group_members WHERE group_id = %s",
                (group_id,)
            )
            
            # 发送给所有在线的群成员(除了发送者)
            for member in members:
                user_id = member['user_id']

                    
                if user_id in self.online_users:
                    response = {
                        'action': 'new_group_message',
                        'group_id': group_id,
                        'message': {
                            **message,  # 修复语法错误
                            'is_self': False
                        }
                    }
                    await self.send_to_user(user_id, response)
        except Exception as e:
            logger.error(f"处理群聊消息出错: {e}", exc_info=True)
    
    async def handle_create_group(self, websocket, data):
        """处理创建群组请求"""
        try:
            creator_id = data.get('creator_id')
            group_name = data.get('group_name', '').strip()
            initial_members = data.get('initial_members', [])
            
            if not creator_id or not group_name:
                await self.send_error(websocket, '缺少必要参数')
                return
                
            result = self.group_service.create_group(creator_id, group_name, initial_members)
            if not result['success']:
                await self.send_error(websocket, result.get('error', '创建群组失败'))
                return
            
            # 通知创建者
            response = {
                'action': 'group_created',
                'group_id': result['group_id'],
                'group_name': result['group_name']
            }
            await self.send_to_user(creator_id, response)
            
            # 通知初始成员
            for member_id in initial_members:
                if member_id in self.online_users:
                    await self.send_to_user(member_id, {
                        'action': 'added_to_group',
                        'group_id': result['group_id'],
                        'group_name': result['group_name']
                    })

                    await self.send_group_list(member_id)
            await self.broadcast_all_users()
        except Exception as e:
            logger.error(f"创建群组处理出错: {e}", exc_info=True)
            await self.send_error(websocket, '创建群组失败')
    
    async def handle_add_friend(self, websocket, data):
        """处理添加好友请求"""
        try:
            from_user_id = data.get('from_user_id')
            to_user_id = data.get('to_user_id')
            
            if not from_user_id or not to_user_id:
                await self.send_error(websocket, '缺少必要参数')
                return
                
            result = self.friend_service.send_request(from_user_id, to_user_id)
            if not result['success']:
                await self.send_error(websocket, result.get('error', '发送好友请求失败'))
                return
            
            # 通知接收方
            if to_user_id in self.online_users:
                from_user = self.db.execute_query(
                    "SELECT username FROM users WHERE user_id = %s",
                    (from_user_id,)
                )
                if from_user and len(from_user) > 0:
                    await self.send_to_user(to_user_id, {
                        'action': 'friend_request',
                        'from_user_id': from_user_id,
                        'from_username': from_user[0]['username']
                    })
        except Exception as e:
            logger.error(f"添加好友处理出错: {e}", exc_info=True)
            await self.send_error(websocket, '添加好友失败')
    
    async def handle_accept_friend(self, websocket, data):
        """处理接受好友请求"""
        try:
            request_id = data.get('request_id')
            current_user_id = data.get('current_user_id')
            action = data.get('action')  # 'accept' or 'reject'
            
            if not request_id or not current_user_id or not action:
                await self.send_error(websocket, '缺少必要参数')
                return
                
            result = self.friend_service.handle_request(request_id, current_user_id, action)
            if not result['success']:
                await self.send_error(websocket, result.get('error', '处理好友请求失败'))
                return
            
            if action == 'accept':
                # 通知当前用户
                await self.send_to_user(current_user_id, {
                    'action': 'friend_added',
                    'friend_id': result.get('friend_info', {}).get('user_id'),
                    'friend_info': result.get('friend_info')
                })
                
                # 通知对方用户
                request = self.db.execute_query(
                    "SELECT user1_id, user2_id FROM friends WHERE relation_id = %s",
                    (request_id,)
                )
                if request and len(request) > 0:
                    request = request[0]
                    other_user_id = request['user1_id'] if request['user2_id'] == current_user_id else request['user2_id']
                    
                    if other_user_id in self.online_users:
                        current_user = self.db.execute_query(
                            "SELECT username FROM users WHERE user_id = %s",
                            (current_user_id,)
                        )
                        if current_user and len(current_user) > 0:
                            await self.send_to_user(other_user_id, {
                                'action': 'friend_added',
                                'friend_id': current_user_id,
                                'friend_info': {
                                    'user_id': current_user_id,
                                    'username': current_user[0]['username']
                                }
                            })
        except Exception as e:
            logger.error(f"接受好友处理出错: {e}", exc_info=True)
            await self.send_error(websocket, '处理好友请求失败')
    
    async def handle_update_nickname(self, websocket, data):
        """处理更新昵称请求"""
        try:
            user_name = data.get('username')
            new_nickname = data.get('nickname', '').strip()
            
            if not user_name or not new_nickname:
                await self.send_error(websocket, '缺少必要参数')
                return
                
            # 更新数据库
            result = self.db.execute_update(
                "UPDATE users SET username = %s WHERE username = %s",
                (new_nickname, user_name)
            )
            user_id = self.db.execute_query("SELECT user_id FROM users WHERE username = %s",(user_name,))
            user_id = user_id[0]['user_id'] if user_id else None
            if result > 0:
                # 通知用户
                await self.send_to_user(user_id, {
                    'action': 'nickname_updated',
                    'success': True,
                    'new_nickname': new_nickname
                })
                
                # 通知好友
                friends = self.friend_service.get_friends(user_id)
                if friends['success']:
                    for friend in friends['friends']:
                        friend_id = friend['user_id']
                        if friend_id in self.online_users:
                            await self.send_to_user(friend_id, {
                                'action': 'friend_nickname_updated',
                                'friend_id': user_id,
                                'new_nickname': new_nickname
                            })
            else:
                await self.send_error(websocket, '更新昵称失败')
        except Exception as e:
            logger.error(f"更新昵称处理出错: {e}", exc_info=True)
            await self.send_error(websocket, '更新昵称失败')
    
    async def handle_get_pending_requests(self, websocket, data):
        """处理获取待处理好友请求"""
        try:
            user_id = data.get('user_id')
            if not user_id:
                await self.send_error(websocket, '缺少用户ID')
                return
                
            requests = self.friend_service.get_pending_requests(user_id)
            if requests['success']:
                response = {
                    'action': 'pending_requests',
                    'requests': requests['requests']
                }
                await self.send_to_user(user_id, response)
            else:
                await self.send_error(websocket, '获取待处理请求失败')
        except Exception as e:
            logger.error(f"获取待处理请求出错: {e}", exc_info=True)
            await self.send_error(websocket, '获取待处理请求失败')

# 启动服务器
async def main():
    server = ChatServer()
    async with websockets.serve(server.handle_connection, "0.0.0.0", 8765):
        logger.info("Chat server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())