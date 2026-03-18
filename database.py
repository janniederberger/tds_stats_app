# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 09:18:40 2026

@author: niederberger jan
"""

# database.py

import psycopg2
import streamlit as st


def get_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=6543
    )


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # --- PLAYERS ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    )
    """)

    # --- GAMES ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id SERIAL PRIMARY KEY,
        date TEXT,
        player_count INTEGER,
        winning_team TEXT
    )
    """)

    # --- PARTICIPATIONS ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS participations (
        id SERIAL PRIMARY KEY,
        game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
        player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
        role TEXT,
        won INTEGER
    )
    """)

    conn.commit()
    cur.close()
    conn.close()