import sqlite3
from auth import register_user, authenticate
from database import add_expense, delete_expense, get_connection, initialize_database

def test_password_is_not_plaintext_and_ownership(db_path):
    register_user("alice","secure123","secure123",db_path)
    conn=get_connection(db_path)
    row=conn.execute("SELECT password_hash FROM users WHERE username=?",("alice",)).fetchone()
    assert row["password_hash"] != "secure123"
    conn.close()
    eid=add_expense("alice",{"date":"2026-10-01","category":"Food","amount":10,
        "payment_method":"Cash","description":"","merchant":"","tags":""},db_path)
    assert not delete_expense("mallory",eid,db_path)
    assert authenticate("alice","secure123",db_path)

def test_legacy_migration(tmp_path):
    path=tmp_path/"legacy.db"
    conn=sqlite3.connect(path)
    conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL)")
    conn.execute("INSERT INTO users(username,password) VALUES('legacy','oldpass123')")
    conn.execute("""CREATE TABLE expenses(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL,date TEXT NOT NULL,
      category TEXT NOT NULL,amount REAL NOT NULL,payment_method TEXT NOT NULL,description TEXT)""")
    conn.execute("INSERT INTO expenses(username,date,category,amount,payment_method,description) VALUES('legacy','2025-02-01','Food',20,'Cash','Tea')")
    conn.execute("CREATE TABLE budgets(username TEXT PRIMARY KEY,budget REAL DEFAULT 0)")
    conn.execute("INSERT INTO budgets VALUES('legacy',500)")
    conn.commit(); conn.close()
    backup=initialize_database(path)
    assert backup and (tmp_path/"legacy.db.pre_campuscash_backup").exists()
    assert authenticate("legacy","oldpass123",path)
    conn=sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]==1
    assert conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0]==1
    assert conn.execute("SELECT password FROM users WHERE username='legacy'").fetchone()[0] != "oldpass123"
    conn.close()
    initialize_database(path)
