"""初始化业务分析库（SQLite）及示例表（销售额 + 班级管理测试数据）。"""

import sqlite3

from app.config import get_settings

DDL = """
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    amount REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_code TEXT NOT NULL UNIQUE,
    class_name TEXT NOT NULL,
    grade TEXT NOT NULL,
    head_teacher TEXT NOT NULL,
    room_no TEXT,
    max_capacity INTEGER NOT NULL DEFAULT 40
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    gender TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    math_score REAL,
    english_score REAL,
    FOREIGN KEY (class_id) REFERENCES classes(id)
);
"""


def _seed_sales_if_empty(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT COUNT(*) FROM sales")
    if cur.fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO sales (month, amount) VALUES (?, ?)",
            [
                ("2024-01", 120.5),
                ("2024-02", 200.0),
                ("2024-03", 95.0),
                ("2024-04", 200.0),
            ],
        )


def _seed_class_demo_if_empty(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT COUNT(*) FROM classes")
    if cur.fetchone()[0] > 0:
        return

    conn.executemany(
        """
        INSERT INTO classes (class_code, class_name, grade, head_teacher, room_no, max_capacity)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("G301", "三年级一班", "三年级", "张老师", "301", 45),
            ("G302", "三年级二班", "三年级", "李老师", "302", 45),
            ("G401", "四年级一班", "四年级", "王老师", "401", 45),
        ],
    )

    def cid(code: str) -> int:
        row = conn.execute(
            "SELECT id FROM classes WHERE class_code = ?",
            (code,),
        ).fetchone()
        assert row is not None
        return int(row[0])

    g301, g302, g401 = cid("G301"), cid("G302"), cid("G401")

    conn.executemany(
        """
        INSERT INTO students (student_no, name, gender, class_id, math_score, english_score)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("S2024001", "陈一", "男", g301, 88.0, 90.0),
            ("S2024002", "刘二", "女", g301, 92.0, 85.0),
            ("S2024003", "黄三", "男", g301, 76.5, 82.0),
            ("S2024004", "赵四", "女", g301, 81.0, 88.5),
            ("S2024005", "周五", "男", g301, 95.0, 91.0),
            ("S2024011", "吴六", "女", g302, 84.0, 79.0),
            ("S2024012", "郑七", "男", g302, 78.0, 86.0),
            ("S2024013", "孙八", "女", g302, 90.0, 92.0),
            ("S2024014", "钱九", "男", g302, 72.0, 74.0),
            ("S2024015", "冯十", "女", g302, 86.0, 80.0),
            ("S2024016", "陈十一", "男", g302, 80.0, 83.0),
            ("S2024101", "楚十二", "女", g401, 91.0, 89.0),
            ("S2024102", "卫十三", "男", g401, 87.0, 84.0),
            ("S2024103", "蒋十四", "女", g401, 93.0, 95.0),
            ("S2024104", "沈十五", "男", g401, 79.0, 81.0),
        ],
    )


def seed_if_empty() -> None:
    settings = get_settings()
    settings.analytics_db_path.parent.mkdir(parents=True, exist_ok=True)
    path = settings.analytics_db_path
    conn = sqlite3.connect(path)
    try:
        conn.executescript(DDL)
        _seed_sales_if_empty(conn)
        _seed_class_demo_if_empty(conn)
        conn.commit()
    finally:
        conn.close()
