# -*- coding: utf-8 -*-
import sys
import json
sys.path.insert(0, 'D:/web_project/4/')
from sql_program import DatabaseManager, GroupService

def application(environ, start_response):
    try:
        if environ['REQUEST_METHOD'] == 'POST':
            # 参数解析
            request_body = environ['wsgi.input'].read(int(environ.get('CONTENT_LENGTH', 0)))
            data = json.loads(request_body.decode('utf-8'))
            
            # 参数校验
            required_fields = ['creator_id', 'group_name']
            if not all(field in data for field in required_fields):
                raise KeyError("缺少必要参数")
                
            # 执行创建
            gs = GroupService(DatabaseManager())
            result = gs.create_group(
                int(data['creator_id']),
                data['group_name'].strip(),
                [int(m) for m in data.get('members', [])]
            )

            # 响应处理
            status = '200 OK' if result['success'] else '400 Bad Request'
            response_body = json.dumps(result).encode('utf-8')
            start_response(status, [('Content-Type', 'application/json')])
            return [response_body]

    except Exception as e:
        sys.stderr.write(f"错误详情: {str(e)}\n")  # 输出到日志
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [b'Internal Server big problem Error']
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    a = environ['PATH_INFO']
    return a
                        