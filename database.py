# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 09:18:40 2026

@author: niederberger jan
"""

import sqlite3

DB_NAME = "tds_stats.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        player_count INTEGER,
        winning_team TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS participations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        player_id INTEGER,
        role TEXT,
        won INTEGER
    )
    """)

    conn.commit()
    conn.close()