import sqlite3

db_path = r"c:\Users\carol\Downloads\tr4cking-app\tr4cking\db.sqlite3"
out_path = r"c:\Users\carol\Downloads\tr4cking-app\tr4cking\scratch\inspect_output.txt"

with open(out_path, "w", encoding="utf-8") as f:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(fleet_bus);")
        columns = cursor.fetchall()
        f.write("Columns in fleet_bus:\n")
        for col in columns:
            f.write(f"{col}\n")
        conn.close()
    except Exception as e:
        f.write(f"Error: {e}\n")
