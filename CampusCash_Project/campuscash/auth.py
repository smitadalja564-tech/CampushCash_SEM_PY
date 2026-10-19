import bcrypt
from database import get_connection

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False

def validate_password(password: str):
    if len(password) < 8:
        return "Use at least 8 characters."
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        return "Include at least one letter and one number."
    return None

def register_user(username, password, confirm, db_path=None):
    username = (username or "").strip()
    if not username or len(username) > 50 or not username.replace("_", "").replace("-", "").isalnum():
        return False, "Username must be 1–50 characters and contain only letters, numbers, _ or -."
    error = validate_password(password or "")
    if error:
        return False, error
    if password != confirm:
        return False, "Passwords do not match."
    conn = get_connection(db_path)
    try:
        hashed = hash_password(password)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        # Legacy tables may still have a NOT NULL `password` column. Store the
        # hash there too, never the submitted plaintext, until the user migrates.
        if "password" in columns:
            conn.execute("INSERT INTO users(username, password_hash, password) VALUES (?, ?, ?)",
                         (username, hashed, hashed))
        else:
            conn.execute("INSERT INTO users(username, password_hash) VALUES (?, ?)",
                         (username, hashed))
        conn.commit()
        return True, "Account created. You can now sign in."
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return False, "That username is already taken."
        raise
    finally:
        conn.close()

def authenticate(username, password, db_path=None):
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE username = ?",
                           ((username or "").strip(),)).fetchone()
        return bool(row and verify_password(password or "", row["password_hash"]))
    finally:
        conn.close()
