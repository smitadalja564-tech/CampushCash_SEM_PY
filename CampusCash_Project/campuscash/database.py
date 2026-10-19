"""SQLite persistence and idempotent migration from the original desktop app."""
import os, sqlite3, shutil
from datetime import date
from pathlib import Path

DEFAULT_CATEGORIES = [
    ("Food", "#F59E0B", "fork-knife"), ("Transportation", "#4185F4", "bus"),
    ("Education", "#6C4CF1", "book-open"), ("Shopping", "#EC4899", "shopping-bag"),
    ("Entertainment", "#8B5CF6", "clapperboard"), ("Medical", "#EF4444", "heart-pulse"),
    ("Bills", "#14B8A6", "receipt"), ("Accommodation", "#64748B", "house"),
    ("Personal Care", "#F97316", "sparkles"), ("Other", "#737B91", "shapes")
]
DEFAULT_DB = os.environ.get("CAMPUSCASH_DB", "student_expense.db")

def get_connection(db_path=None):
    path = str(db_path or DEFAULT_DB)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn

def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}

def initialize_database(db_path=None):
    path = Path(db_path or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(path)
    try:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        # Back up a legacy database before making any schema changes.
        legacy = "users" in tables and "password_hash" not in _columns(conn, "users")
        legacy = legacy or ("budgets" in tables and "month" not in _columns(conn, "budgets"))
        backup = None
        if legacy and path.exists() and path.stat().st_size:
            backup = Path(str(path) + ".pre_campuscash_backup")
            if not backup.exists():
                shutil.copy2(path, backup)

        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        # Migrate original users table. The legacy password column is overwritten
        # with the bcrypt hash too, so plaintext credentials are not retained.
        user_cols = _columns(conn, "users")
        if "password_hash" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            rows = conn.execute("SELECT id, password FROM users").fetchall() if "password" in user_cols else []
            import bcrypt
            for row in rows:
                old = row["password"] or ""
                hashed = bcrypt.hashpw(old.encode(), bcrypt.gensalt()).decode()
                conn.execute("UPDATE users SET password_hash=?, password=? WHERE id=?",
                             (hashed, hashed, row["id"]))
            conn.execute("UPDATE users SET password_hash=? WHERE password_hash IS NULL", ("!invalid-legacy-password!",))
        if "created_at" not in _columns(conn, "users"):
            conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT")

        conn.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            payment_method TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            merchant TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        exp_cols = _columns(conn, "expenses")
        for col in ("merchant", "tags"):
            if col not in exp_cols:
                conn.execute(f"ALTER TABLE expenses ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
        # Preserve original budgets and migrate their unknown period to the current
        # month, explicitly noted in README and the UI.
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "budgets" in tables and "month" not in _columns(conn, "budgets"):
            if "budgets_legacy" not in tables:
                conn.execute("ALTER TABLE budgets RENAME TO budgets_legacy")
            else:
                conn.execute("DROP TABLE budgets")
        conn.execute("""CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            month TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0 CHECK(amount >= 0),
            UNIQUE(username, month)
        )""")
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "budgets_legacy" in tables:
            legacy_rows = conn.execute("SELECT username, budget FROM budgets_legacy").fetchall()
            current_month = date.today().strftime("%Y-%m")
            for row in legacy_rows:
                if conn.execute("SELECT 1 FROM users WHERE username=?", (row["username"],)).fetchone():
                    conn.execute("""INSERT OR IGNORE INTO budgets(username, month, amount)
                                    VALUES (?, ?, ?)""",
                                 (row["username"], current_month, max(0, float(row["budget"] or 0))))
        conn.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#6C4CF1',
            icon TEXT NOT NULL DEFAULT 'shapes',
            archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
            UNIQUE(username, name)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS settings (
            username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
            currency TEXT NOT NULL DEFAULT 'INR',
            date_format TEXT NOT NULL DEFAULT 'YYYY-MM-DD',
            appearance TEXT NOT NULL DEFAULT 'Light'
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(username, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses(username, category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_budgets_user_month ON budgets(username, month)")
        for row in conn.execute("SELECT username FROM users").fetchall():
            username = row["username"]
            conn.execute("INSERT OR IGNORE INTO settings(username) VALUES (?)", (username,))
            for name, color, icon in DEFAULT_CATEGORIES:
                conn.execute("INSERT OR IGNORE INTO categories(username,name,color,icon) VALUES (?,?,?,?)",
                             (username, name, color, icon))
        conn.commit()
        return str(backup) if backup else None
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def ensure_user_defaults(username, db_path=None):
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT OR IGNORE INTO settings(username) VALUES (?)", (username,))
        for name, color, icon in DEFAULT_CATEGORIES:
            conn.execute("INSERT OR IGNORE INTO categories(username,name,color,icon) VALUES (?,?,?,?)",
                         (username, name, color, icon))
        conn.commit()
    finally:
        conn.close()

def add_expense(username, data, db_path=None):
    conn = get_connection(db_path)
    try:
        cur = conn.execute("""INSERT INTO expenses
            (username,date,category,amount,payment_method,description,merchant,tags)
            VALUES (?,?,?,?,?,?,?,?)""",
            (username, data["date"], data["category"], float(data["amount"]),
             data["payment_method"], data.get("description","").strip(),
             data.get("merchant","").strip(), data.get("tags","").strip()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_expense(username, expense_id, data, db_path=None):
    conn = get_connection(db_path)
    try:
        cur = conn.execute("""UPDATE expenses SET date=?,category=?,amount=?,payment_method=?,
            description=?,merchant=?,tags=? WHERE id=? AND username=?""",
            (data["date"], data["category"], float(data["amount"]), data["payment_method"],
             data.get("description","").strip(), data.get("merchant","").strip(),
             data.get("tags","").strip(), int(expense_id), username))
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()

def delete_expense(username, expense_id, db_path=None):
    conn = get_connection(db_path)
    try:
        cur = conn.execute("DELETE FROM expenses WHERE id=? AND username=?",
                           (int(expense_id), username))
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()

def get_expenses(username, db_path=None, start=None, end=None, category=None, payment=None,
                 search=None, min_amount=None, max_amount=None, sort="newest"):
    import pandas as pd
    conn = get_connection(db_path)
    try:
        sql = """SELECT id,date,category,amount,payment_method,description,merchant,tags
                 FROM expenses WHERE username=?"""
        args = [username]
        if start: sql += " AND date>=?"; args.append(str(start))
        if end: sql += " AND date<=?"; args.append(str(end))
        if category and category != "All": sql += " AND category=?"; args.append(category)
        if payment and payment != "All": sql += " AND payment_method=?"; args.append(payment)
        if search:
            sql += " AND (description LIKE ? OR merchant LIKE ? OR tags LIKE ?)"
            term = f"%{search}%"; args.extend([term, term, term])
        if min_amount is not None: sql += " AND amount>=?"; args.append(float(min_amount))
        if max_amount is not None: sql += " AND amount<=?"; args.append(float(max_amount))
        ordering = {"newest":"date DESC,id DESC","oldest":"date ASC,id ASC",
                    "amount high":"amount DESC","amount low":"amount ASC"}.get(sort, "date DESC,id DESC")
        sql += " ORDER BY " + ordering
        return pd.read_sql_query(sql, conn, params=args)
    finally:
        conn.close()

def monthly_total(username, month, db_path=None):
    conn = get_connection(db_path)
    try:
        row = conn.execute("""SELECT COALESCE(SUM(amount),0) total, COUNT(*) n
            FROM expenses WHERE username=? AND date>=? AND date<?""",
            (username, month+"-01", _next_month(month))).fetchone()
        return float(row["total"]), int(row["n"])
    finally:
        conn.close()

def _next_month(month):
    y, m = map(int, month.split("-"))
    return f"{y+1:04d}-01" if m == 12 else f"{y:04d}-{m+1:02d}"

def get_budget(username, month, db_path=None):
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT amount FROM budgets WHERE username=? AND month=?",
                           (username, month)).fetchone()
        return float(row["amount"]) if row else 0.0
    finally:
        conn.close()

def save_budget(username, month, amount, db_path=None):
    conn = get_connection(db_path)
    try:
        conn.execute("""INSERT INTO budgets(username,month,amount) VALUES (?,?,?)
            ON CONFLICT(username,month) DO UPDATE SET amount=excluded.amount""",
            (username, month, float(amount)))
        conn.commit()
    finally:
        conn.close()

def get_categories(username, include_archived=False, db_path=None):
    conn = get_connection(db_path)
    try:
        sql = "SELECT id,name,color,icon,archived FROM categories WHERE username=?"
        if not include_archived: sql += " AND archived=0"
        sql += " ORDER BY archived,name"
        return [dict(r) for r in conn.execute(sql, (username,)).fetchall()]
    finally:
        conn.close()

def save_setting(username, currency, date_format, appearance, db_path=None):
    conn = get_connection(db_path)
    try:
        conn.execute("""INSERT INTO settings(username,currency,date_format,appearance)
          VALUES (?,?,?,?) ON CONFLICT(username) DO UPDATE SET
          currency=excluded.currency,date_format=excluded.date_format,appearance=excluded.appearance""",
          (username,currency,date_format,appearance))
        conn.commit()
    finally:
        conn.close()

def get_settings(username, db_path=None):
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT currency,date_format,appearance FROM settings WHERE username=?",
                           (username,)).fetchone()
        return dict(row) if row else {"currency":"INR","date_format":"YYYY-MM-DD","appearance":"Light"}
    finally:
        conn.close()
