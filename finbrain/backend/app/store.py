"""SQLite persistence. Sensitive logs, questions, answers and drafts are encrypted."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
from pathlib import Path

from cryptography.fernet import Fernet


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class Store:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        supplied = os.getenv('FINBRAIN_DATA_KEY')
        key_path = root / 'local.key'
        if supplied:
            key = supplied.encode()
        elif key_path.exists():
            key = key_path.read_bytes()
        else:
            if (root / 'finbrain.db').exists():
                raise RuntimeError('Existing database has no local key. Restore local.key or configure FINBRAIN_DATA_KEY; do not regenerate a key for existing encrypted data.')
            key = Fernet.generate_key()
            key_path.write_bytes(key)
        self.key = key
        self.cipher = Fernet(key)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(root / 'finbrain.db', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, uid TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS queries (id TEXT PRIMARY KEY, uid TEXT, snapshot TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, previous TEXT, payload TEXT, hash TEXT);
            CREATE TABLE IF NOT EXISTS analytics (topic TEXT, window TEXT, subject TEXT, unresolved INTEGER DEFAULT 0, PRIMARY KEY(topic,window,subject));
            CREATE TABLE IF NOT EXISTS releases (topic TEXT, window TEXT, payload TEXT, PRIMARY KEY(topic,window));
            CREATE TABLE IF NOT EXISTS reads (uid TEXT, rid TEXT, version INTEGER, PRIMARY KEY(uid,rid));
            CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, owner TEXT, snapshot TEXT, status TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS overlays (rid TEXT PRIMARY KEY, snapshot TEXT, payload TEXT);
        ''')
        self.db.commit()

    def seal(self, value):
        return self.cipher.encrypt(canonical(value).encode()).decode()

    def unseal(self, value):
        return json.loads(self.cipher.decrypt(value.encode()))

    def execute(self, sql, args=()):
        with self.lock:
            result = self.db.execute(sql, args)
            self.db.commit()
            return result

    def all(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def setting(self, key, default=None):
        rows = self.all('SELECT value FROM settings WHERE key=?', (key,))
        return rows[0]['value'] if rows else default

    def set_setting(self, key, value):
        self.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, str(value)))

    def pseudonym(self, uid, window):
        return hmac.new(self.key, f'analytics:{window}:{uid}'.encode(), hashlib.sha256).hexdigest()

    def audit(self, payload):
        with self.lock:
            rows = self.all('SELECT hash FROM audit ORDER BY seq DESC LIMIT 1')
            prev = rows[0]['hash'] if rows else '0' * 64
            encrypted = self.seal(payload)
            digest = hmac.new(self.key, (prev + encrypted).encode(), hashlib.sha256).hexdigest()
            self.execute('INSERT INTO audit(previous,payload,hash) VALUES (?,?,?)', (prev, encrypted, digest))

    def verify_audit(self):
        prev = '0' * 64
        for row in self.all('SELECT * FROM audit ORDER BY seq'):
            expected = hmac.new(self.key, (prev + row['payload']).encode(), hashlib.sha256).hexdigest()
            if row['previous'] != prev or not hmac.compare_digest(expected, row['hash']):
                return False
            prev = row['hash']
        return True

    def close(self):
        self.db.close()
