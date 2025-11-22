
import sqlite3
import pandas as pd

DB_PATH = 'hearthstone.db'
TABLE_NAME = 'keywords'

def inspect_table():
    """
    Connects to the database and inspects the schema and content of a table.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Inspecting table '{TABLE_NAME}' in '{DB_PATH}'...")

        # Print table schema
        print("\n--- Schema ---")
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({TABLE_NAME});")
        schema = cur.fetchall()
        if schema:
            df_schema = pd.DataFrame(schema, columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'])
            print(df_schema)
        else:
            print(f"Table '{TABLE_NAME}' not found.")
            return

        # Print first 5 rows
        print(f"\n--- First 5 Rows ---")
        try:
            df_content = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME} LIMIT 5;", conn)
            if not df_content.empty:
                print(df_content)
            else:
                print("Table is empty.")
        except pd.io.sql.DatabaseError as e:
            print(f"Error reading table content: {e}")


    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    inspect_table()
