
from database.connection import get_connection
from pathlib import Path

sql_file = Path(__file__).parent / "demo_queries.sql"

sql = sql_file.read_text()

conn = get_connection()
cur = conn.cursor()

try:
    # Execute each SQL statement separately
    statements = [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]

    for i, statement in enumerate(statements, 1):
        print(f"\n{'=' * 60}")
        print(f"QUERY {i}")
        print("=" * 60)

        cur.execute(statement)

        if cur.description:
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            print(columns)

            for row in rows[:20]:
                print(row)

            print(f"\nRows returned: {len(rows)}")
        else:
            print("Query executed successfully.")

finally:
    cur.close()
    conn.close()
