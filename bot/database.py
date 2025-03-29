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
    cur.execute("""
        INSERT INTO user_tasks (user_id, task, dedline) 
        VALUES (%s, %s, %s) 
        RETURNING id
    """, (user_id, task, dedline))
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return task_id

def get_user_tasks(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, task, dedline 
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
    cur.execute("""
        SELECT id, user_id, task 
        FROM user_tasks 
        WHERE dedline = %s
    """, (current_time,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return tasks  # Возвращаем список кортежей (id, user_id, task)

def close_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Переносим задачу в архив
        cur.execute("""
            INSERT INTO archive_tasks (task_id, user_id, task, task_closed_date)
            SELECT id, user_id, task, NOW() 
            FROM user_tasks 
            WHERE id = %s
            RETURNING task_id
        """, (task_id,))
        
        # Удаляем из активных задач
        cur.execute("DELETE FROM user_tasks WHERE id = %s", (task_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при закрытии задачи: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def update_task_deadline(task_id, new_deadline):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE user_tasks 
            SET dedline = %s 
            WHERE id = %s
            RETURNING id
        """, (new_deadline, task_id))
        conn.commit()
        return cur.fetchone() is not None
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при обновлении дедлайна: {e}")
        return False
    finally:
        cur.close()
        conn.close()