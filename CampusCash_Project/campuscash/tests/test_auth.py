from auth import register_user, authenticate, hash_password, verify_password

def test_register_and_login(db_path):
    ok, _ = register_user("student1", "campus123", "campus123", db_path)
    assert ok
    assert authenticate("student1", "campus123", db_path)
    assert not authenticate("student1", "wrongpass", db_path)

def test_password_hashing():
    hashed = hash_password("campus123")
    assert hashed != "campus123"
    assert verify_password("campus123", hashed)
    assert not verify_password("wrongpass", hashed)

def test_validation_and_duplicate(db_path):
    assert not register_user("x", "short", "short", db_path)[0]
    assert not register_user("student", "abc12345", "nope", db_path)[0]
    assert register_user("student", "abc12345", "abc12345", db_path)[0]
    assert not register_user("student", "abc12345", "abc12345", db_path)[0]
