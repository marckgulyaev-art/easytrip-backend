import os, json, hmac, hashlib, time, sqlite3
from urllib.parse import parse_qsl
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DATABASE_PATH", "easytrip.db")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://marckgulyaev-art.github.io").split(",")
app = FastAPI(title="EasyTrip API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in ALLOWED_ORIGINS if x.strip()], allow_credentials=False, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "X-Telegram-Init-Data"])

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("CREATE TABLE IF NOT EXISTS users(telegram_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, username TEXT, xp INTEGER NOT NULL DEFAULT 0, trips INTEGER NOT NULL DEFAULT 0, mission INTEGER NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        con.execute("CREATE TABLE IF NOT EXISTS visited_countries(id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, country TEXT NOT NULL, added_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(telegram_id,country))")
        con.execute("CREATE TABLE IF NOT EXISTS favorites(id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, destination TEXT NOT NULL, description TEXT DEFAULT '', emoji TEXT DEFAULT '❤️', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(telegram_id,destination))")
@app.on_event("startup")
def startup(): init_db()

def verify_telegram_init_data(init_data: str):
    if not BOT_TOKEN: raise HTTPException(500, "Backend BOT_TOKEN is not configured")
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True)); received_hash = parsed.pop("hash"); auth_date = int(parsed.get("auth_date", "0"))
    except Exception: raise HTTPException(401, "Invalid Telegram initData")
    if not auth_date or abs(time.time()-auth_date)>86400: raise HTTPException(401, "Telegram initData expired")
    data_check_string = "\n".join(f"{k}={v}" for k,v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash): raise HTTPException(401, "Telegram signature verification failed")
    try: return json.loads(parsed["user"])
    except Exception: raise HTTPException(401, "Telegram user missing")

def telegram_user(init_data: Optional[str]):
    if not init_data: raise HTTPException(401, "Open this app from Telegram")
    return verify_telegram_init_data(init_data)

def upsert_user(u):
    tid=int(u["id"])
    with db() as con:
        con.execute("INSERT INTO users(telegram_id,first_name,last_name,username) VALUES(?,?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET first_name=excluded.first_name,last_name=excluded.last_name,username=excluded.username,updated_at=CURRENT_TIMESTAMP", (tid,u.get("first_name",""),u.get("last_name",""),u.get("username","")))
        row=con.execute("SELECT * FROM users WHERE telegram_id=?",(tid,)).fetchone()
    return dict(row)

def user_countries(tid):
    with db() as con: return [r["country"] for r in con.execute("SELECT country FROM visited_countries WHERE telegram_id=? ORDER BY added_at",(tid,)).fetchall()]

def user_favorites(tid):
    with db() as con: return [dict(r) for r in con.execute("SELECT id,destination,description,emoji,created_at FROM favorites WHERE telegram_id=? ORDER BY created_at DESC",(tid,)).fetchall()]

def level_for_xp(xp):
    levels=[("Новичок",0,"🧳"),("Турист",500,"✈️"),("Исследователь",1500,"🧭"),("Авантюрист",4000,"🎒"),("Легенда",10000,"👑")]
    current=levels[0]; nxt=levels[1]
    for i,l in enumerate(levels):
        if xp>=l[1]: current=l; nxt=levels[i+1] if i+1<len(levels) else None
    return {"name":current[0],"number":levels.index(current)+1,"icon":current[2],"next_xp":nxt[1] if nxt else None}

class CountryPayload(BaseModel): country: str
class FavoritePayload(BaseModel): destination: str; description: str = ""; emoji: str = "❤️"

@app.get("/health")
def health(): return {"status":"ok","service":"EasyTrip API"}
@app.get("/api/profile")
def profile(x_telegram_init_data: Optional[str]=Header(default=None)):
    u=telegram_user(x_telegram_init_data); user=upsert_user(u); countries=user_countries(user["telegram_id"]); xp=user["xp"]
    favs=user_favorites(user["telegram_id"])
    return {"user":{"id":user["telegram_id"],"first_name":user["first_name"],"last_name":user["last_name"],"username":user["username"]},"xp":xp,"trips":user["trips"],"mission":user["mission"],"visited":countries,"stampList":countries,"favorites":favs,"level":level_for_xp(xp)}
@app.post("/api/countries")
def add_country(payload: CountryPayload, x_telegram_init_data: Optional[str]=Header(default=None)):
    u=telegram_user(x_telegram_init_data); name=payload.country.strip()
    if not name or len(name)>80: raise HTTPException(400,"Country name is invalid")
    tid=int(u["id"])
    with db() as con:
        con.execute("INSERT OR IGNORE INTO users(telegram_id,first_name,last_name,username) VALUES(?,?,?,?)",(tid,u.get("first_name",""),u.get("last_name",""),u.get("username","")))
        cur=con.execute("INSERT OR IGNORE INTO visited_countries(telegram_id,country) VALUES(?,?)",(tid,name))
        if cur.rowcount: con.execute("UPDATE users SET xp=xp+150,updated_at=CURRENT_TIMESTAMP WHERE telegram_id=?",(tid,))
        user=con.execute("SELECT xp FROM users WHERE telegram_id=?",(tid,)).fetchone()
    return {"added":bool(cur.rowcount),"visited":user_countries(tid),"xp":user["xp"],"level":level_for_xp(user["xp"])}
@app.post("/api/xp")
def add_xp(xp: int, x_telegram_init_data: Optional[str]=Header(default=None)):
    u=telegram_user(x_telegram_init_data)
    if xp<0 or xp>500: raise HTTPException(400,"XP amount out of range")
    tid=int(u["id"]); upsert_user(u)
    with db() as con:
        con.execute("UPDATE users SET xp=xp+?,updated_at=CURRENT_TIMESTAMP WHERE telegram_id=?",(xp,tid)); user=con.execute("SELECT xp FROM users WHERE telegram_id=?",(tid,)).fetchone()
    return {"xp":user["xp"],"level":level_for_xp(user["xp"])}
@app.get("/api/favorites")
def get_favorites(x_telegram_init_data: Optional[str]=Header(default=None)):
    u=telegram_user(x_telegram_init_data); upsert_user(u)
    return {"favorites":user_favorites(int(u["id"]))}
@app.post("/api/favorites")
def add_favorite(payload: FavoritePayload, x_telegram_init_data: Optional[str]=Header(default=None)):
    u=telegram_user(x_telegram_init_data); destination=payload.destination.strip(); description=payload.description.strip(); emoji=payload.emoji.strip() or "❤️"
    if not destination or len(destination)>120: raise HTTPException(400,"Destination is invalid")
    tid=int(u["id"]); upsert_user(u)
    with db() as con:
        cur=con.execute("INSERT OR IGNORE INTO favorites(telegram_id,destination,description,emoji) VALUES(?,?,?,?)",(tid,destination,description[:200],emoji[:8]))
    return {"added":bool(cur.rowcount),"favorites":user_favorites(tid)}
@app.delete("/api/favorites/{favorite_id}")
def delete_favorite(favorite_id: int, x_telegram_init_data: Optional[str]=Header(default=None)):
    u=telegram_user(x_telegram_init_data); tid=int(u["id"])
    with db() as con: cur=con.execute("DELETE FROM favorites WHERE id=? AND telegram_id=?",(favorite_id,tid))
    return {"deleted":bool(cur.rowcount),"favorites":user_favorites(tid)}
