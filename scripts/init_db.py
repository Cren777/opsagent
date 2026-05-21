#!/usr/bin/env python3
"""初始化 MySQL 数据库：建表 + 种子数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from config.settings import settings


def get_connection():
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        charset=settings.mysql_charset,
    )


def main():
    print(f"连接 MySQL {settings.mysql_host}:{settings.mysql_port} ...")
    conn = get_connection()
    cursor = conn.cursor()

    schema_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "db_schema", "schema.sql"
    )
    seed_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "db_schema", "seed_data.sql"
    )

    print(f"执行 {schema_file} ...")
    with open(schema_file, "r", encoding="utf-8") as f:
        for statement in f.read().split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    cursor.execute(stmt)
                except pymysql.err.OperationalError as e:
                    if "Unknown database" in str(e) or "database exists" not in str(e):
                        print(f"  [跳过] {stmt[:60]}... => {e}")

    print(f"执行 {seed_file} ...")
    cursor.execute("USE ops_agent")
    with open(seed_file, "r", encoding="utf-8") as f:
        content = f.read()
        # Execute statements that don't start with comment
        for statement in content.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    if "Duplicate" in str(e) or "already exists" in str(e):
                        pass  # 幂等重跑
                    else:
                        print(f"  [警告] {stmt[:60]}... => {e}")

    conn.commit()

    # 验证
    tables = ["servers", "services", "alerts", "users", "tickets", "performance_metrics"]
    print("\n验证数据：")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} 行")

    cursor.close()
    conn.close()
    print("\n数据库初始化完成！")


if __name__ == "__main__":
    main()
