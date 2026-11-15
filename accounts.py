"""TraceFort's server-side store: accounts, sign-in tokens, sign-in lockouts and contact messages.

Everything lives in one SQLite database on the server (data/tracefort.db, gitignored). The browser only
ever holds a random sign-in token in a cookie. No email, no real password, no personal data beyond a
first name, an optional work ZIP code and home preferences.

- PINs: PBKDF2-SHA256, 200,000 rounds, random 16-byte salt per user. Never stored as plain text.
- Lockout: 5 wrong PINs in a row locks that name for 15 minutes (a 4-digit PIN is otherwise guessable).
- ponytail: SQLite on one machine is right for the demo. Hosted (e.g. Streamlit Cloud) wipes local files on
  restart, so a real launch moves this to a hosted database like Postgres.
"""
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB = Path(__file__).parent / "data" / "tracefort.db"   # gitignored
PIN_ROUNDS = 200_000
TERMS_VERSION = "2026-11-14"   # bump when the Terms or Privacy Policy change; stored with each account
MAX_FAILS, LOCK_SECONDS = 5, 15 * 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    key TEXT PRIMARY KEY, name TEXT NOT NULL, salt TEXT NOT NULL, pin TEXT NOT NULL, prefs TEXT NOT NULL,
    created INTEGER NOT NULL, agreed_terms TEXT, agreed_at INTEGER);
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY, user_key TEXT NOT NULL REFERENCES users(key) ON DELETE CASCADE, created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, fails INTEGER NOT NULL, locked_until INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL, name TEXT, message TEXT NOT NULL);
"""


@contextmanager
def _db():
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def _key(name):
    return " ".join(str(name).lower().split())


def _hash(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), PIN_ROUNDS).hex()


# ---------------------------------------------------------------------------------- lockout -----
def lock_remaining(key):
    """Seconds until this name (or "__admin__") can try again; 0 = not locked."""
    with _db() as con:
        row = con.execute("SELECT locked_until FROM attempts WHERE key = ?", (_key(key),)).fetchone()
    return max(0, row["locked_until"] - int(time.time())) if row else 0


def attempt(key, ok):
    """Record one PIN try. Returns False without counting while locked; 5 misses in a row lock it."""
    key = _key(key)
    if lock_remaining(key):
        return False
    with _db() as con:
        if ok:
            con.execute("DELETE FROM attempts WHERE key = ?", (key,))
            return True
        row = con.execute("SELECT fails FROM attempts WHERE key = ?", (key,)).fetchone()
        fails = (row["fails"] if row else 0) + 1
        locked = int(time.time()) + LOCK_SECONDS if fails >= MAX_FAILS else 0
        con.execute("INSERT OR REPLACE INTO attempts (key, fails, locked_until) VALUES (?, ?, ?)",
                    (key, 0 if locked else fails, locked))
    return False


# --------------------------------------------------------------------------------- accounts -----
def check_new(name, pin):
    """Problem with a new name/PIN as a sentence, or None if fine."""
    if not _key(name):
        return "Please enter a first name."
    if len(name.strip()) > 40:
        return "Please use a shorter name (40 letters max)."
    if not (len(pin) == 4 and pin.isdigit()):
        return "Your PIN needs to be exactly 4 numbers."
    with _db() as con:
        taken = con.execute("SELECT 1 FROM users WHERE key = ?", (_key(name),)).fetchone()
    if taken:
        return f"That name is taken. Add your last initial, like “{name.strip()} R.”"
    return None


def _new_token(con, key):
    token = secrets.token_urlsafe(24)
    con.execute("INSERT INTO tokens (token, user_key, created) VALUES (?, ?, ?)", (token, key, int(time.time())))
    return token


def create(name, pin, prefs, agreed=False):
    """New account -> token. `agreed` = ticked "18+ and I agree to the Terms and Privacy Policy".
    Raises ValueError with a friendly message."""
    problem = check_new(name, pin)
    if problem:
        raise ValueError(problem)
    if not agreed:
        raise ValueError("To make an account, confirm you're 18 or older and agree to the Terms and Privacy Policy.")
    salt, now, key = secrets.token_hex(16), int(time.time()), _key(name)
    with _db() as con:
        con.execute("INSERT INTO users (key, name, salt, pin, prefs, created, agreed_terms, agreed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (key, name.strip(), salt, _hash(pin, salt), json.dumps(prefs), now, TERMS_VERSION, now))
        return _new_token(con, key)


def sign_in(name, pin):
    """Token if name + PIN match and the name isn't locked, else None (see lock_remaining)."""
    key = _key(name)
    if lock_remaining(key):
        return None
    with _db() as con:
        user = con.execute("SELECT salt, pin FROM users WHERE key = ?", (key,)).fetchone()
    ok = bool(user) and secrets.compare_digest(_hash(pin, user["salt"]), user["pin"])
    if not attempt(key, ok):                      # unknown names count too, so names can't be probed
        return None
    with _db() as con:
        return _new_token(con, key)


def _user_by_token(con, token):
    if not isinstance(token, str) or not token:        # a cookie is untrusted input: only plain text tokens
        return None
    return con.execute("SELECT u.* FROM tokens t JOIN users u ON u.key = t.user_key WHERE t.token = ?",
                       (token,)).fetchone()


def from_token(token):
    """{'name', 'prefs'} for a remembered browser, or None."""
    with _db() as con:
        user = _user_by_token(con, token)
    return {"name": user["name"], "prefs": json.loads(user["prefs"])} if user else None


def save_prefs(token, prefs):
    with _db() as con:
        con.execute("UPDATE users SET prefs = ? WHERE key = (SELECT user_key FROM tokens WHERE token = ?)",
                    (json.dumps(prefs), token))


def sign_out(token):
    with _db() as con:
        con.execute("DELETE FROM tokens WHERE token = ?", (token,))


def export(token):
    """Everything we hold about this account, minus the PIN hash and salt (for "Download my data")."""
    with _db() as con:
        user = _user_by_token(con, token)
    if not user:
        return None
    data = {k: user[k] for k in user.keys() if k not in ("pin", "salt", "key")}
    data["prefs"] = json.loads(data["prefs"])
    return data


def delete_account(token):
    """Delete the account and sign it out everywhere. True if something was deleted."""
    with _db() as con:
        user = _user_by_token(con, token)
        if not user:
            return False
        con.execute("DELETE FROM users WHERE key = ?", (user["key"],))   # tokens go with it (ON DELETE CASCADE)
    return True


# --------------------------------------------------------------------------------- messages -----
def save_message(name, message):
    with _db() as con:
        con.execute("INSERT INTO messages (at, name, message) VALUES (?, ?, ?)",
                    (int(time.time()), name.strip()[:40], message.strip()[:2000]))


def list_messages():
    with _db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM messages ORDER BY at DESC, id DESC")]


def delete_message(message_id):
    with _db() as con:
        con.execute("DELETE FROM messages WHERE id = ?", (message_id,))


if __name__ == "__main__":
    import tempfile

    DB = Path(tempfile.mkdtemp()) / "test.db"                       # never touch the real database
    prefs = {"budget": 180000, "goal": "Live in it"}
    assert check_new("", "1234") and check_new("Sam", "12a4") and check_new("Sam", "123")
    try:
        create("Sam", "1234", prefs)                                # didn't tick the agreement box
        raise AssertionError("account created without agreeing to the Terms")
    except ValueError:
        pass
    t = create("Sam", "1234", prefs, agreed=True)
    assert from_token(t) == {"name": "Sam", "prefs": prefs}
    assert export(t)["agreed_terms"] == TERMS_VERSION and not {"pin", "salt"} & set(export(t))
    assert check_new(" sam ", "9999") is not None                 # same name, any spacing/case
    save_prefs(t, {**prefs, "budget": 200000})
    assert from_token(t)["prefs"]["budget"] == 200000
    sign_out(t)
    assert from_token(t) is None                                   # signed out = forgotten
    t2 = sign_in("Sam", "1234")
    assert from_token(t2)["prefs"]["budget"] == 200000             # answers survive sign-out
    assert b"1234" not in DB.read_bytes()                          # PIN never stored in plain text

    # lockout: 4 misses are fine, the 5th locks, and even the right PIN is refused while locked
    for _ in range(4):
        assert sign_in("Sam", "0000") is None
    assert lock_remaining("Sam") == 0 and sign_in("Sam", "1234")   # success resets the count
    for _ in range(5):
        sign_in("Sam", "0000")
    assert lock_remaining("Sam") > 0 and sign_in("Sam", "1234") is None
    for _ in range(5):                                             # unknown names lock too
        sign_in("Nobody", "1111")
    assert lock_remaining("nobody") > 0

    t3 = create("Ana", "4321", prefs, agreed=True)
    t4 = sign_in("Ana", "4321")                                    # second device
    assert delete_account(t3) and from_token(t3) is None and from_token(t4) is None   # gone everywhere
    assert check_new("Ana", "4321") is None                        # name free again

    save_message("Lee", "Is this real?")
    save_message("", "Hello")
    msgs = list_messages()
    assert [m["message"] for m in msgs] == ["Hello", "Is this real?"]
    delete_message(msgs[0]["id"])
    assert len(list_messages()) == 1
    print("accounts self-checks passed")
