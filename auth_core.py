"""Учебная ролевая модель для интерфейса Streamlit."""
import os,json,hashlib,hmac,secrets,time
from pathlib import Path
ROLES={"admin":{"view","create","schedule","export"},"engineer":{"view","create","schedule","export"},"student":{"view","schedule","export"}}
def hash_password(password,salt=None):
    salt=salt or secrets.token_hex(16)
    hashed=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),200000).hex()
    return f"pbkdf2_sha256$200000${salt}${hashed}"
def verify(password,stored):
    try:
        _,iterations,salt,expected=stored.split("$")
        calculated=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),int(iterations)).hex()
        return hmac.compare_digest(calculated,expected)
    except (ValueError,TypeError):return False
def load_users():
    p=Path(os.getenv("AUTH_FILE",Path(__file__).with_name("users.json")))
    data=json.loads(p.read_text(encoding="utf-8"))
    if any(u.get("role") not in ROLES or not u.get("password_hash","").startswith("pbkdf2_sha256$") for u in data):raise ValueError("Некорректный файл пользователей")
    return data
def authenticate(login,password):
    for u in load_users():
        if hmac.compare_digest(u["login"],login) and verify(password,u["password_hash"]):return {"login":u["login"],"role":u["role"]}
    return None
def allowed(role,action):return action in ROLES.get(role,set())
