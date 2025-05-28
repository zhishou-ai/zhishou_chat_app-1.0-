import mysql.connector.pooling
from typing import List, Dict, Optional
import hashlib
import secrets
import re
import time




class DatabaseManager:
    #数据库操作管家    
    def __init__(self):
        self.pool = self._create_connection_pool()
    def _create_connection_pool(self):
        #创建连接池
        return mysql.connector.pooling.MySQLConnectionPool(
            pool_name="zhishou_chat_pool",
            pool_size=5,
            host="localhost",
            user = "chat_app",
            password = "zhishou_chat",
            database = "zhishou_chat_app",
            autocommit=True,
        )
    def id_username(self, user_id: int) -> Optional[str]:
        a = self.execute_query("SELECT username FROM users WHERE user_id = %s", (user_id,))
        return a[0]["username"] if a else None
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        #执行查询语句（返回字典列表）
        with self.pool.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    def execute_update(self, sql: str, params: tuple = None) -> int:
        #执行更新语句（返回受影响的行数）
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return cursor.rowcount
    def execute_friend_query(self, user_id: int) -> List[Dict]:
        #查询好友列表
        sql = """
            SELECT
                u.user_id, u.username, u.avater, u.status,
                f.relation_id, f.status as friend_status,
            FROM
                friends f
            JOIN
                users u ON u.user_id = CASE
                    WHEN f.user1_id = %s THEN f.user2_id
                    ELSE f.user1_id
                END
            WHERE
                f.user1_id = %s OR f.user2_id = %s
            AND f.relation_type = 'friend'
            """
        return self.execute_query(sql, (user_id, user_id, user_id))
            

    def _get_connection(self):
        #获取连接
        return self.pool.get_connection()
    
    def get_all_users(self):
        """获取所有用户列表"""
        sql = "SELECT user_id, username, avatar FROM users"
        return self.execute_query(sql)

    def get_user_groups(self, user_id: int):
        """获取用户加入的所有群组"""
        sql = """
            SELECT g.group_id, g.group_name, g.avatar 
            FROM group_members gm
            JOIN `groups` g ON g.group_id = gm.group_id
            WHERE gm.user_id = %s
        """
        return self.execute_query(sql, (user_id,))





class AuthService:
    def __init__(self,db_manager:DatabaseManager):
        self.db = db_manager
    def _is_locked(self, username: str) -> bool:
        #只检查数据库中的锁定状态
        """
        检查用户是否被锁定
        1. 查询数据库中的锁定状态
        2. 如果锁定，返回True，否则返回False
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT attempt_count FROM login_attempts WHERE username = %s", (username,))
            record = cursor.fetchone()
            if record and record["attempt_count"] >= 5:
                return True
            return False
    def _hash_password(self, password: str) -> str:
        #哈希密码
        """
        密码哈希处理
        安全要点：
        1. 使用secrets生成加密盐（防止彩虹表攻击）
        2. 密码在前盐在后（password+salt比salt+password更抗GPU破解）
        3. 固定输出格式：salt$hash
        """
        salt = secrets.token_hex(8)
        hash_obj = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${hash_obj}"
    def _validate_username(self, username: str) -> bool:
        #验证用户名
        """
        用户名验证规则：
        1. 只能包含字母、数字
        2, 长度在3到20之间
        3. 不允许使用空格和特殊字符
        """
        if len(username) < 3 or len(username) > 20:
            return False
        if not re.match(r"^[a-zA-Z0-9]+$", username):
            return False
        return True
    def _validate_email(self, email: str) -> bool:
        #简易验证邮箱
        return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))
    def _check_existing(self, username: str, email:Optional[str]) ->Optional[Dict]:
        """
        检查用户名/邮箱是否已存在
        优化点：
        1. 使用字典游标(dictionary=True)提升可读性
        2. 明确区分用户名冲突和邮箱冲突
        3. 提前返回避免不必要的查询
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, email FROM users WHERE username = %s OR email = %s", (username, email or ""))
            for row in cursor:
                if row["username"] == username:
                    return {"success":False,"error": "用户名已被注册"}
                if email and row["email"] == email:
                    return {"success":False,"error": "邮箱已被注册"}
            return None
    def register_user(self, username: str, password: str, email: Optional[str] = None) -> Dict:
        """
        输入格式register_user(username,password,email（可选）)
        返回值：
        成功    
        失败{“success”:False,”error”:错误信息}
        """
        """
        用户注册流程优化版
        分层设计：
        1. 输入验证 → 2. 唯一性检查 → 3. 密码哈希 → 4. 数据库插入
        """
        if not self._validate_username(username):
            return {"success":False,"error": "用户名需要在3到20个字符之间，且只能包含字母和数字"}
        if email and not self._validate_email(email):
            return {"success":False,"error": "邮箱格式不正确"}
        if not password:
            return {"success":False,"error": "密码不能为空"}
        if existing_error := self._check_existing(username, email):
            return existing_error
        password_hash = self._hash_password(password)
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)", (username, password_hash, email))
                return {"success":True,"user_id": cursor.lastrowid,"username": username}
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
    def _clean_expired_records(self):
        #清理数据库里过期的失败记录
        """
        清理数据库中超过300秒的登录失败记录
        1. 使用DELETE语句删除过期记录
        2. 使用ON DUPLICATE KEY UPDATE避免重复插入
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM login_attempts WHERE last_attempt < %s", (int(time.time()) - 300,))


    def login_user(self, username: str, password: str) -> Dict:
        """
        输入格式login_user(username,password)
        返回值：
        成功{“success”:True,”user_id”:用户ID,”username”:用户名}
        失败{“success”:False,”error”:错误信息}
        """
        # 自动清理过期记录
        self._clean_expired_records()
        if self._is_locked(username):
            #显示剩余时间
            with self.db._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT last_attempt FROM login_attempts WHERE username = %s", (username,))
                record = cursor.fetchone()
                if record:
                    remaining = 300 - (int(time.time()) - record["last_attempt"])
                    return {"success": False, "error": f"账号被锁定，请等待{remaining}秒后再试"}
        #清理数据库中的过期记录
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM login_attempts WHERE last_attempt < %s", (int(time.time()) - 300,))
        #调用优化后的登录方法
        result = self._attempt_login_user(username, password)
        if result["success"]:
            #重置数据库中的登录失败次数
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE login_attempts SET attempt_count = 0 WHERE username = %s", (username,))
            
        else:
            #记录登录失败次数
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO login_attempts (username, attempt_count, last_attempt) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE attempt_count = attempt_count + 1, last_attempt = %s", (username, 1, time.time(), time.time()))
        return result
    

    def _attempt_login_user(self, username: str, password: str) -> Dict:
        """
        用户登录流程优化版
        1. 输入验证 → 2. 数据库查询 → 3. 密码验证 → 4. 返回结果
        返回值：
        成功{“success”:True,”user_id”:用户ID,”username”:用户名}
        失败{“success”:False,”error”:错误信息}
        """
        #基础输入验证
        if not self._validate_username(username):
            return {"success":False,"error": "用户名需要在3到20个字符之间，且只能包含字母和数字"}
        if not password:
            return {"success":False,"error": "密码不能为空"}
        try:
            #2.查询用户信息
            with self.db._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT user_id, username, password_hash FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if not user:
                    return {"success":False,"error": "用户名或密码错误"}
                #3.验证密码
                if self._verify_password(password,user["password_hash"]):
                    return {"success":True,"user_id": user["user_id"],"username": user["username"]}
                else:
                    return {"success":False,"error": "用户名或密码错误"}
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
        

    def _verify_password(self, input_password: str, stored_hash: str) -> bool:
        """
        验证密码
        1. 分离盐和哈希值
        2. 使用相同的哈希算法验证输入密码
        """
        try:
            salt,correct_hash = stored_hash.split("$")
            #使用相同的哈希算法验证输入密码
            input_hash = hashlib.sha256((input_password + salt).encode()).hexdigest()
            return secrets.compare_digest(input_hash, correct_hash)
        except ValueError:
            return False
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
        




class FriendService:
    def __init__(self,db:DatabaseManager):
        self.db = db
    def send_request(self, from_user_id: int, to_user_id: int) -> Dict:
        if from_user_id == to_user_id:
            return {"success":False,"error":"不能添加自己为好友"}
        #确保user_id1 <user_id2
        if from_user_id > to_user_id:
            from_user_id, to_user_id = to_user_id, from_user_id
        user1 ,user2 = from_user_id, to_user_id
        #检查是否已经是好友
        existing = self.db.execute_query("SELECT relation_id,status FROM friends WHERE (user1_id = %s AND user2_id = %s)", (user1, user2))
        if existing:
            status = existing[0]["status"]
            if status == "accepted":
                return {"success":False,"error":"已经是好友了"}
            elif status == "pending":
                return {"success":False,"error":"已经发送好友请求了"}
        #插入好友请求
        try:
            affected = self.db.execute_update("INSERT INTO friends (user1_id, user2_id, status, action_user_id) VALUES (%s, %s, 'pending', %s)", (user1, user2, from_user_id))
            return {"success": affected > 0}
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
        


    def get_friends(self, user_id: int) -> Dict:
        sql = """
            SELECT
                u.user_id, 
                u.username, 
                u.avatar,
                f.status as friend_status,
                CASE
                    WHEN f.action_user_id = %s THEN %s
                    ELSE %s
                END as request_type
            FROM friends f
            JOIN users u ON u.user_id = CASE
                WHEN f.user1_id = %s THEN f.user2_id
                ELSE f.user1_id
                END
            WHERE (f.user1_id = %s OR f.user2_id = %s)
        """
        return {
            "success": True,
            "friends": self.db.execute_query(
                sql,
                (user_id, "outgoing", "incoming", user_id, user_id, user_id)
            )
        }
    

    def handle_request(self, request_id: int, current_user_id: int, action: str) -> Dict:
        #处理好友请求(同意/拒绝)
        check_sql = "SELECT user1_id, user2_id,status,action_user_id FROM friends WHERE relation_id = %s AND status = 'pending'"
        request = self.db.execute_query(check_sql, (request_id,))
        if not request:
            return {"success":False,"error":"请求不存在或已处理"}
        request = request[0]
        other_user_id = request["user1_id"] if request["user2_id"] == current_user_id else request["user2_id"]
        if request["action_user_id"] == current_user_id:
            return {"success":False,"error":"不能处理自己的请求"}
        try:
            if action == "accept":
                update_sql = "UPDATE friends SET status = 'accepted',relation_type = 'friend' WHERE relation_id = %s"
                self.db.execute_update(update_sql, (request_id,))
                #返回成功信息及对方用户信息
                user_info = self.db.execute_query("SELECT user_id,username,avatar FROM users WHERE user_id = %s", (other_user_id,))[0]
                return {
                    "success":True,
                    "message":"好友请求已接受",
                    "friend_info":user_info
                }
            elif action == "reject":
                self.db.execute_update("DELETE FROM friends WHERE relation_id = %s", (request_id,))
                return {"success":True,"message":"好友请求已拒绝"}
            else:
                return {"success":False,"error":"无效的操作"}
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
        



    def get_pending_requests(self, user_id: int) -> Dict:
        sql = """
            SELECT
                f.relation_id, 
                u.user_id as sender_id, 
                u.username, 
                u.avatar
                FROM friends f
                JOIN users u ON f.action_user_id = u.user_id
                WHERE(f.user1_id = %s OR f.user2_id = %s) AND f.status = 'pending' AND
                f.action_user_id != %s"""
        return {"success":True,"requests":self.db.execute_query(sql,(user_id,user_id,user_id))}
    def remove_friend(self, user_id: int, friend_id: int) -> Dict:
        #删除好友关系
        if user_id == friend_id:
            return {"success":False,"error":"不能删除自己"}
        #确保user_id1 <user_id2
        if user_id > friend_id:
            user1 ,user2 = friend_id, user_id
        else:
            user1 ,user2 = user_id, friend_id
        #检查是否是好友
        existing = self.db.execute_query("SELECT relation_id,status FROM friends WHERE (user1_id = %s AND user2_id = %s) AND status = 'friend'", (user1, user2))
        if not existing:
            return {"success":False,"error":"不是好友关系"}
        #删除好友关系
        try:
            affected = self.db.execute_update("DELETE FROM friends WHERE relation_id = %s", (existing[0]["relation_id"],))
            return {"success": affected > 0}
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
        




class GroupService:
    def __init__(self,db:DatabaseManager):
        self.db = db
class GroupService:
    def __init__(self,db:DatabaseManager):
        self.db = db
        
    def create_group(self, creator_id: int, group_name: str, initial_members: List[int] = None) -> Dict:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                conn.autocommit = False  # 显式关闭自动提交

                # 群名称验证
                if not (2 <= len(group_name) <= 64):
                    raise ValueError("群名称长度需要在2到64个字符之间")

                # 验证创建者是否存在
                if not self._user_exists(creator_id):
                    raise ValueError("创建者不存在")

                # 创建群组
                cursor.execute("""
                    INSERT INTO `groups` (group_name, creator_id)
                    VALUES (%s, %s)
                """, (group_name, creator_id))
                group_id = cursor.lastrowid

                # 添加创建者（使用REPLACE防止重复）
                cursor.execute("""
                    REPLACE INTO group_members 
                    (group_id, user_id, role)
                    VALUES (%s, %s, 'owner')
                """, (group_id, creator_id))

                # 处理成员列表
                if initial_members:
                    # 去重并排除创建者
                    members = list(set(initial_members))
                    members = [m for m in members if m != creator_id]
                    
                    # 批量验证用户存在性
                    placeholders = ','.join(['%s']*len(members))
                    valid_users = self.db.execute_query(
                        f"SELECT user_id FROM users WHERE user_id IN ({placeholders})",
                        tuple(members)
                    )
                    valid_ids = [u['user_id'] for u in valid_users]

                    # 批量插入（使用IGNORE防止重复）
                    if valid_ids:
                        values = [(group_id, uid, 'member') for uid in valid_ids]
                        cursor.executemany("""
                            INSERT IGNORE INTO group_members 
                            (group_id, user_id, role)
                            VALUES (%s, %s, %s)
                        """, values)

                conn.commit()
                return {"success": True, "group_id": group_id, "group_name": group_name}

        except mysql.connector.Error as err:
            conn.rollback()
            return {"success": False, "error": f"数据库错误: {err}"}
        except ValueError as ve:
            conn.rollback()
            return {"success": False, "error": str(ve)}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": "系统错误"}
        except mysql.connector.Error as err:
            if 'conn' in locals():  # 检查连接是否存在
                conn.rollback()
            return {"success": False, "error": f"数据库错误: {err}"}
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            return {"success": False, "error": "系统错误"}

    def _user_exists(self, user_id: int) -> bool:
        result = self.db.execute_query(
            "SELECT 1 FROM users WHERE user_id = %s",
            (user_id,)
        )
        return bool(result)


    def get_user_groups(self, user_id: int) -> Dict:
        """获取用户群组列表（包含实时成员数）"""
        sql = """
        SELECT 
            g.group_id, 
            g.group_name, 
            g.avatar,
            gm.role,
            (SELECT COUNT(*) FROM group_members WHERE group_id = g.group_id) AS member_count
        FROM group_members gm
        JOIN `groups` g ON g.group_id = gm.group_id
        WHERE gm.user_id = %s
        """
        return {"success":True,"groups":self.db.execute_query(sql, (user_id,))}
    


    def add_member(self, group_id: int, new_user_id: int, inviter_id: int) -> Dict:
        role_check = self.db.execute_query("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, inviter_id))
        if not role_check or role_check[0]["role"] not in ["owner","admin"]:
            return {"success":False,"error":"没有权限添加成员"}
        #检查成员是否已经在群里
        existing_member = self.db.execute_query(
            "SELECT * FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, new_user_id)
        )
        if existing_member:
            return {"success": False, "error": "用户已经是群组成员"}
        # 添加群组成员
        try:
            self.db.execute_update(
            """
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (%s, %s, 'member')
            """, (group_id, new_user_id)
            )
            return {"success": True}
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
        

class MessageService:
    def __init__(self):
        self.db = DatabaseManager()

    def _is_group_member(self, user_id: int, group_id: int) -> bool:
        """检查用户是否是群成员"""
        sql = "SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s"
        result = self.db.execute_query(sql, (group_id, user_id))
        return bool(result)

    def send_message(
        self,
        sender_id:int,
        receiver_type:str,
        receiver_id:int,
        content: str,
        content_type: str = 'text',
        file_url:Optional[str] = None
    ) -> Dict:
        #发送消息
        if not self._user_exists(sender_id):
            return {"success":False,"error":"发送者不存在"}
        if receiver_type == "private":
            if not self._user_exists(receiver_id):
                return {"success":False,"error":"接收者不存在"}

        elif receiver_type == "group":
            if not self._group_exists(receiver_id):
                return {"success":False,"error":"群组不存在"}
            if not self._is_group_member(sender_id, receiver_id):
                return {"success":False,"error":"不是群组成员"}
        else:
            return {"success":False,"error":"无效的接收者类型"}
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                #插入消息
                cursor.execute("""INSERT INTO messages 
                               (sender_id, receiver_type, receiver_id, content, content_type, file_url) 
                                VALUES (%s, %s, %s, %s, %s, %s)""",
                               (sender_id, receiver_type, receiver_id, content, content_type, file_url))
                msg_id = cursor.lastrowid
                #返回成功信息及消息ID
                msg_id = cursor.lastrowid
            return {"success":True,"msg_id":msg_id}
        except mysql.connector.Error as err:
            return {"success":False,"error": f"数据库错误: {err}"}
        
    def _user_exists(self, user_id: int) -> bool:
        #检查用户是否存在
        sql = "SELECT 1 FROM users WHERE user_id = %s"
        result = self.db.execute_query(sql, (user_id,))
        return bool(result)
    
    def _group_exists(self, group_id: int) -> bool:
        #检查群组是否存在
        sql = "SELECT 1 FROM `groups` WHERE group_id = %s"
        result = self.db.execute_query(sql, (group_id,))
        return bool(result)

    def get_messages(self, user_id: int, receiver_type: str, receiver_id: int, page:int = 1, page_size :int = 20) -> Dict:
        #获取消息列表
        try:
            offset = (page - 1) * page_size
            """
            SELECT
                f.relation_id, 
                u.user_id as sender_id, 
                u.username, 
                u.avatar
                FROM friends f
                JOIN users u ON f.action_user_id = u.user_id
                WHERE(f.user1_id = %s OR f.user2_id = %s) AND f.status = 'pending' AND
                f.action_user_id != %s"""
            # ================= 关键修改 =================
            if receiver_type == "private":
                # 私聊需匹配双方对话关系
                sql = """
                    SELECT 
                        u.username as sender_name,
                        m.msg_id,
                        m.sender_id, 
                        m.content,
                        m.content_type, 
                        m.file_url, 
                        m.created_at
                    FROM users u
                    JOIN messages m ON u.user_id = m.sender_id
                    WHERE receiver_type = %s
                    AND (
                        (sender_id = %s AND receiver_id = %s)
                        OR
                        (sender_id = %s AND receiver_id = %s)
                    )
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                params = (receiver_type, user_id, receiver_id, receiver_id, user_id, page_size, offset)
            else:
                # 群聊保持原逻辑
                sql = """
                    SELECT 
                        msg_id, sender_id, content, content_type, file_url, created_at
                    FROM messages
                    WHERE receiver_type = %s AND receiver_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                params = (receiver_type, receiver_id, page_size, offset)
            # ==============================================
            
            messages = self.db.execute_query(sql, params)
            print(messages)
            return {"success": True, "messages": messages}
        except mysql.connector.Error as err:
            return {"success": False, "error": f"数据库错误: {err}"}
            
        
if __name__ == "__main__":
    Db = DatabaseManager()
    auth = AuthService(Db)
    friend_service = FriendService(Db)
    gs = GroupService(Db)
    ms = MessageService()
    '''
    print(Db.execute_update("delete from messages"))
    #print(Db.execute_update("DELETE FROM `group_members`")) 
    #print(Db.execute_update("DELETE FROM `groups`"))

    #print(auth.register_user("niu", "123456"))
    print(ms.send_message(35,"private",36,"你好呀！"))
    print(ms.get_messages(35, "private", 36))

    #print(gs.create_group(35, "测试群组", [36, 37, 38]))
    print(ms.send_message(35, "group", 8, "群组消息sfdgghjkjhgfds测试"))
    #print(gs.create_group(35, "AI小组", [36, 37, 38]))

    print(ms.send_message(35, "group", 11, "项目做完了吗？"))

'''
    print(Db.execute_update("DELETE FROM group_members"))
    print(Db.execute_update("DELETE FROM `groups`"))
    print(Db.execute_update("ALTER TABLE `groups` AUTO_INCREMENT = 1"))
    print(Db.execute_update("ALTER TABLE `group_members` AUTO_INCREMENT = 1"))
    print(Db.execute_update("DELETE FROM friends"))
    print(Db.execute_update("DELETE FROM messages"))
    print(Db.execute_update("DELETE FROM login_attempts"))
    print(Db.execute_update("DELETE FROM users"))
    print(Db.execute_update("ALTER TABLE `users` AUTO_INCREMENT = 1"))
    print(Db.execute_update("ALTER TABLE `messages` AUTO_INCREMENT = 1"))
    #print(ms.get_messages("1", "private", "2"))
    #print(ms.send_message(1, "private", 2, "你好！"))
    print(auth.login_user("yushiyuan", "1234567"))
    #print(ms.get_messages(1, "private", 2))






