# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'D:/web_project/4/')
from sql_program import DatabaseManager, AuthService   

def application(environ, start_response):
    # 获取请求方法
    request_method = environ.get('REQUEST_METHOD', '')
    
    if request_method == 'POST' and environ['PATH_INFO'] == '/sign_in':
        # 处理 POST 请求
        post_data = environ['wsgi.input'].read().decode('utf-8')
        
        # 解析表单数据
        fields = {}
        for field in post_data.split('&'):
            key, value = field.split('=')
            fields[key] = value
        
        username = fields.get('username', '')
        password = fields.get('password', '')

        Db = DatabaseManager()
        auth = AuthService(Db)
        result = auth.login_user(username, password)

        # 验证用户名和密码（示例逻辑）
        if result['success'] == True:
            try:
                with open('D:/web_project/4/html/main_web.html', 'r', encoding='utf-8') as f:
                    response_body = f.read()
                # 在页面末尾插入JS，保存user_id到localStorage
                insert_js = f"""
<script>
    localStorage.setItem('currentUserId', '{result["user_id"]}');
</script>
"""
                # 如果main_web.html有</body>，插入到前面；否则直接加到最后
                if '</body>' in response_body:
                    response_body = response_body.replace('</body>', insert_js + '</body>')
                else:
                    response_body += insert_js

                status = '200 OK'
                response_headers = [
                    ('Content-Type', 'text/html; charset=utf-8'),
                    ('Content-Length', str(len(response_body.encode('utf-8'))))
                ]

            except FileNotFoundError:
            # 如果文件不存在，返回 404 错误
                response_body = "404 Not Found"
                status = '404 Not Found'
                response_headers = [
                    ('Content-Type', 'text/plain'),
                    ('Content-Length', str(len(response_body)))
                ]
                
        else:
            with open('D:/web_project/4/html/sign_in_failed_web.html', 'r', encoding='utf-8') as f:
                response_body = f.read()
            status = '200 OK'  
            response_headers = [
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Content-Length', str(len(response_body.encode('utf-8'))))
            ]

            '''
            response_body = result['error']
            status = '200 OK'  
            response_headers = [
                ('Content-Type', 'text/plain; charset=utf-8'),
                ('Content-Length', str(len(response_body.encode('utf-8'))))
            ]

            '''

    elif request_method == 'POST' and environ['PATH_INFO'] == '/sign_up':
        # 处理 POST 请求
        post_data = environ['wsgi.input'].read().decode('utf-8')
        
        # 解析表单数据
        fields = {}
        for field in post_data.split('&'):
            key, value = field.split('=')
            fields[key] = value
        
        username = fields.get('username', '')
        password = fields.get('password', '')

        Db = DatabaseManager()
        auth = AuthService(Db)
        result = auth.register_user(username, password)

        # 验证用户名和密码（示例逻辑）
        if result['success'] == True:
            response_body = "成功注册！"
            status = '200 OK'
            response_headers = [
                ('Content-Type', 'text/plain; charset=utf-8'),
                ('Content-Length', str(len(response_body.encode('utf-8'))))
            ]

        else:
            response_body = result['error']
            status = '200 OK'  
            response_headers = [
                ('Content-Type', 'text/plain; charset=utf-8'),
                ('Content-Length', str(len(response_body.encode('utf-8'))))
            ]
    else:
        response_body = "408 Request Time-out"
        status = '408 Request Time-out'
        response_headers = [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(len(response_body.encode('utf-8'))))
        ]



    
    start_response(status, response_headers)
    
    return [response_body.encode('utf-8')]