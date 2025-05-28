# -*- coding: utf-8 -*-
import sys
import json
sys.path.insert(0, 'D:/web_project/4/')
from sql_program import DatabaseManager, MessageService

def application(environ, start_response):
    try:
        # 新增用户列表接口
        if environ['REQUEST_METHOD'] == 'GET' and environ['PATH_INFO'] == '/users':
            db = DatabaseManager()
            users = db.get_all_users()
            response_body = json.dumps(users).encode('utf-8')
            start_response('200 OK', [('Content-Type', 'application/json'), ('Access-Control-Allow-Origin', '*')])
            return [response_body]

        # 新增群组列表接口
        elif environ['REQUEST_METHOD'] == 'GET' and environ['PATH_INFO'] == '/groups':
            query = environ.get('QUERY_STRING', '')
            user_id = None
            for part in query.split('&'):
                if part.startswith('user_id='):
                    user_id = part.split('=')[1]
                    break
            if not user_id or user_id == 'None':
                start_response('400 Bad Request', [('Content-Type', 'application/json')])
                return [json.dumps({"error": "user_id is required"}).encode('utf-8')]
            user_id = int(user_id)
            db = DatabaseManager()
            groups = db.get_user_groups(user_id)
            response_body = json.dumps(groups).encode('utf-8')
            start_response('200 OK', [('Content-Type', 'application/json'), ('Access-Control-Allow-Origin', '*')])
            return [response_body]

        # 消息历史接口
        elif environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'] == '/messages':
            request_length = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_length)
            data = json.loads(request_body.decode('utf-8'))
            user_id_raw = data.get('userId')
            chat_id_raw = data.get('chatId')
            chat_type = data.get('type')
            page = int(data.get('page', 1))
            page_size = int(data.get('pageSize', 20))

            # 参数校验
            if user_id_raw is None or chat_id_raw is None or chat_type is None:
                start_response('400 Bad Request', [('Content-Type', 'application/json')])
                return [json.dumps({"error": "userId, chatId, and type are required"}).encode('utf-8')]
            try:
                user_id = int(user_id_raw)
                chat_id = int(chat_id_raw)
            except Exception:
                start_response('400 Bad Request', [('Content-Type', 'application/json')])
                return [json.dumps({"error": "userId and chatId must be integers"}).encode('utf-8')]

            ms = MessageService()
            result = ms.get_messages(user_id, chat_type, chat_id, page, page_size)
            messages = []

            if result["success"]:
                for msg in result["messages"]:
                    msg_type = "sent" if msg["sender_id"] == user_id else "received"
                    messages.append({
                        "type": msg_type,
                        "content": msg["content"],
                        "sender_id": str(msg["sender_id"]),
                        "senderAvatar": str(msg["sender_id"]),
                        "msg_id": msg["msg_id"]
                    })
                response_body = json.dumps(messages).encode('utf-8')
                start_response('200 OK', [('Content-Type', 'application/json'), ('Access-Control-Allow-Origin', '*')])
                return [response_body]
            else:
                start_response('500 Internal Server Error', [('Content-Type', 'application/json')])
                return [json.dumps({"error": result["error"]}).encode('utf-8')]

        # 用户信息接口
        elif environ['REQUEST_METHOD'] == 'GET' and environ['PATH_INFO'] == '/user_info':
            query = environ.get('QUERY_STRING', '')
            user_id = None
            for part in query.split('&'):
                if part.startswith('id='):
                    user_id = part.split('=')[1]
                    break
            if not user_id or user_id == 'None':
                start_response('400 Bad Request', [('Content-Type', 'application/json')])
                return [json.dumps({"error": "id is required"}).encode('utf-8')]
            try:
                user_id = int(user_id)
            except Exception:
                start_response('400 Bad Request', [('Content-Type', 'application/json')])
                return [json.dumps({"error": "id must be integer"}).encode('utf-8')]
            db = DatabaseManager()
            user = db.execute_query("SELECT user_id, username, avatar FROM users WHERE user_id = %s", (user_id,))
            if user:
                response_body = json.dumps(user[0]).encode('utf-8')
                start_response('200 OK', [('Content-Type', 'application/json'), ('Access-Control-Allow-Origin', '*')])
                return [response_body]
            else:
                start_response('404 Not Found', [('Content-Type', 'application/json')])
                return [json.dumps({"error": "User not found"}).encode('utf-8')]

    except Exception as e:
        sys.stderr.write(f"错误详情: {str(e)}\n")  # 输出到日志
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [b'Internal Server Error']