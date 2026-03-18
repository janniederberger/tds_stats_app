# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 09:18:40 2026

@author: niederberger jan
"""

# database.py
import psycopg2
import pandas as pd
import streamlit as st

# --- Connection ---
def get_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )

# --- Initialize DB ---
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Players table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        );
    """)

    # Games table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            date TIMESTAMP DEFAULT NOW(),
            player_count INT,
            winning_team TEXT
        );
    """)

    # Participations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS participations (
            id SERIAL PRIMARY KEY,
            game_id INT REFERENCES games(id) ON DELETE CASCADE,
            player_id INT REFERENCES players(id) ON DELETE CASCADE,
            role TEXT,
            won BOOLEAN
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

# --- Player Functions ---
def add_player(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO players (name) VALUES (%s) ON CONFLICT DO NOTHING;", (name,))
    conn.commit()
    cur.close()
    conn.close()

def get_players():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM players ORDER BY name;")
    players = cur.fetchall()
    cur.close()
    conn.close()
    return players

# --- Game Functions ---
def add_game(player_count, winning_team):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO games (player_count, winning_team) VALUES (%s, %s) RETURNING id;", (player_count, winning_team))
    game_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return game_id

def add_participation(game_id, player_id, role, won):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO participations (game_id, player_id, role, won)
        VALUES (%s, %s, %s, %s);
    """, (game_id, player_id, role, won))
    conn.commit()
    cur.close()
    conn.close()

def get_games():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, player_count, winning_team FROM games ORDER BY date DESC;")
    games = cur.fetchall()
    cur.close()
    conn.close()
    return games

def get_game_details(game_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT pl.name, pa.role, pa.won
        FROM participations pa
        JOIN players pl ON pl.id = pa.player_id
        WHERE pa.game_id=%s;
    """, (game_id,))
    details = cur.fetchall()
    cur.close()
    conn.close()
    return details

def delete_game(game_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM games WHERE id=%s;", (game_id,))
    conn.commit()
    cur.close()
    conn.close()

# --- Aggregated Player Stats ---
@st.cache_data(ttl=300)
def load_player_stats():
    conn = get_connection()
    query = """
        SELECT
            p.id AS player_id,
            p.name AS player,
            COUNT(pa.game_id) AS games,
            SUM(CASE WHEN pa.won THEN 1 ELSE 0 END)::float / COUNT(pa.game_id) AS winrate,
            SUM(CASE WHEN pa.role='Adventurer' AND pa.won THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN pa.role='Adventurer' THEN 1 ELSE 0 END),0) AS adv_rate,
            SUM(CASE WHEN pa.role='Adventurer' THEN 1 ELSE 0 END) AS adv_games,
            SUM(CASE WHEN pa.role='Guardian' AND pa.won THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN pa.role='Guardian' THEN 1 ELSE 0 END),0) AS guardian_rate,
            SUM(CASE WHEN pa.role='Guardian' THEN 1 ELSE 0 END) AS guard_games
        FROM participations pa
        JOIN players p ON p.id = pa.player_id
        GROUP BY p.id, p.name;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- Player Synergy ---
@st.cache_data(ttl=300)
def load_player_synergies(min_games=3):
    conn = get_connection()
    query = f"""
        SELECT
            pa1.player_id AS player1,
            pa2.player_id AS player2,
            COUNT(DISTINCT pa1.game_id) AS games_together,
            SUM(CASE WHEN pa1.won AND pa2.won THEN 1 ELSE 0 END)::float / COUNT(DISTINCT pa1.game_id) AS winrate
        FROM participations pa1
        JOIN participations pa2 
            ON pa1.game_id = pa2.game_id 
            AND pa1.player_id < pa2.player_id
        GROUP BY pa1.player_id, pa2.player_id
        HAVING COUNT(DISTINCT pa1.game_id) >= {min_games};
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def top_player_synergies(top_n=20, min_games=3):
    df = load_player_synergies(min_games)
    df_sorted = df.sort_values("winrate", ascending=False).head(top_n)
    # Join names
    players = dict(get_players())
    df_sorted["player1"] = df_sorted["player1"].map(players)
    df_sorted["player2"] = df_sorted["player2"].map(players)
    return df_sorted