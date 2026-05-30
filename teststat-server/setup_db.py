import os

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql


def main() -> None:
    load_dotenv()

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASS", "")
    target_db = os.getenv("DB_NAME", "teststat_db")
    maintenance_db = os.getenv("MAINTENANCE_DB", "postgres")

    conn = psycopg2.connect(host=host, port=port, dbname=maintenance_db, user=user, password=password)
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        if cur.fetchone() is None:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
            print(f"created database: {target_db}")
        else:
            print(f"database already exists: {target_db}")

    conn.close()


if __name__ == "__main__":
    main()
