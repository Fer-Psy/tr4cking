import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

with open('db_query_results.md', 'w', encoding='utf-8') as f:
    f.write("# DB Query Results\n\n")

    f.write("## EMPRESAS\n")
    cur.execute("SELECT id, nombre FROM fleet_empresa")
    for row in cur.fetchall():
        f.write(f"- id={row[0]}, nombre={row[1]}\n")

    f.write("\n## ITINERARIOS\n")
    cur.execute("SELECT id, nombre, empresa_id, activo FROM itineraries_itinerario")
    for row in cur.fetchall():
        f.write(f"- id={row[0]}, nombre={row[1]}, empresa_id={row[2]}, activo={row[3]}\n")

    f.write("\n## HORARIOS\n")
    cur.execute("SELECT id, hora_salida, activo FROM itineraries_horario")
    for row in cur.fetchall():
        f.write(f"- id={row[0]}, hora_salida={row[1]}, activo={row[2]}\n")

    f.write("\n## M2M TABLES\n")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%horario%'")
    m2m_tables = cur.fetchall()
    for t in m2m_tables:
        f.write(f"### Table: {t[0]}\n")
        cur.execute(f"SELECT * FROM {t[0]} LIMIT 30")
        cols = [desc[0] for desc in cur.description]
        f.write(f"Columns: {cols}\n")
        for row in cur.fetchall():
            f.write(f"  {row}\n")

conn.close()
f.write("\nDone.\n")
