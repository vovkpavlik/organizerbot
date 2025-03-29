import psycopg2
from config.config import DB_CONFIG

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def check_user_exists(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM user_info WHERE id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

def add_user(user_id, telegram_tag):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_info (id, telegram_tag) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", 
                (user_id, telegram_tag))
    conn.commit()
    cur.close()
    conn.close()

def update_user_name(user_id, name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE user_info SET name = %s WHERE id = %s", (name, user_id))
    conn.commit()
    cur.close()
    conn.close()

def add_task(user_id, task, dedline=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_tasks (user_id, task, dedline) VALUES (%s, %s, %s)", 
                (user_id, task, dedline))
    conn.commit()
    cur.close()
    conn.close()

def get_user_tasks(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT task, dedline 
        FROM user_tasks 
        WHERE user_id = %s 
        ORDER BY dedline ASC NULLS LAST, id
    """, (user_id,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return tasks

def get_due_tasks(current_time):
    conn = get_db_connection()
    cur = conn.cursor()
    # Получаем задачи, дедлайн которых совпадает с текущим временем (минута в минуту)
    cur.execute("""
        SELECT user_id, task 
        FROM user_tasks 
        WHERE dedline = %s
    """, (current_time,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return tasks  # Возвращаем список кортежей (user_id, task)