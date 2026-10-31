"""Local publication receipts; never store credentials or server responses."""
import sqlite3
from datetime import datetime
from pathlib import Path
import settings


def database():
    return settings.APP / 'history.sqlite3'


def connect():
    path=database()
    path.parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(str(path))
    db.execute('CREATE TABLE IF NOT EXISTS publications (id INTEGER PRIMARY KEY, date TEXT NOT NULL, total INTEGER NOT NULL, succeeded INTEGER NOT NULL)')
    return db


def record(total, succeeded):
    with connect() as db:
        db.execute('INSERT INTO publications(date,total,succeeded) VALUES(?,?,?)',
                   (datetime.now().isoformat(timespec='seconds'), int(total), int(succeeded)))


def recent(limit=200):
    with connect() as db:
        return db.execute('SELECT date,total,succeeded FROM publications ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
