$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dbPath = Join-Path $repoRoot "kanban.db"

Write-Output "Applying seed to $dbPath"

@'
import sqlite3
from pathlib import Path

repo = Path(r"__REPO__")
db_path = repo / "kanban.db"
sql_files = [
    repo / "sql" / "20_clean_data.sql",
    repo / "sql" / "30_seed_users.sql",
    repo / "sql" / "40_seed_structure.sql",
    repo / "sql" / "50_seed_tasks.sql",
    repo / "sql" / "55_seed_activity.sql",
]
conn = sqlite3.connect(db_path)
try:
    conn.execute("PRAGMA foreign_keys = ON")
    for file in sql_files:
        conn.executescript(file.read_text(encoding="utf-8"))
    conn.commit()
finally:
    conn.close()
print("Seed applied")
'@.Replace("__REPO__", $repoRoot.Replace("\", "\\")) | .\.venv\Scripts\python -

Write-Output "Verification:"
@'
import sqlite3
from pathlib import Path

repo = Path(r"__REPO__")
db_path = repo / "kanban.db"
sql = (repo / "sql" / "60_verify_seed.sql").read_text(encoding="utf-8").lstrip("\ufeff")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
try:
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        rows = conn.execute(stmt).fetchall()
        if rows:
            print(f"--- {stmt.splitlines()[0][:70]} ---")
            for row in rows:
                print(dict(row))
finally:
    conn.close()
'@.Replace("__REPO__", $repoRoot.Replace("\", "\\")) | .\.venv\Scripts\python -
