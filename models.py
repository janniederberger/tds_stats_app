# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 09:19:43 2026

@author: niederberger jan
"""

# models.py

from database import get_connection
import datetime
import pandas as pd


def add_player(name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO players(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
        (name,)
    )

    conn.commit()
    cur.close()
    conn.close()


def get_players():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM players ORDER BY name")
    players = cur.fetchall()

    cur.close()
    conn.close()
    return players


def add_game(player_count, winning_team):
    conn = get_connection()
    cur = conn.cursor()

    date = datetime.datetime.now().isoformat()

    cur.execute("""
        INSERT INTO games(date, player_count, winning_team)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (date, player_count, winning_team))

    game_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return game_id


def add_participation(game_id, player_id, role, won):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO participations(game_id, player_id, role, won)
        VALUES (%s, %s, %s, %s)
    """, (game_id, player_id, role, int(won)))

    conn.commit()
    cur.close()
    conn.close()


def get_all_participations():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            players.name,
            participations.role,
            participations.won,
            games.player_count,
            games.winning_team,
            games.date,
            participations.game_id
        FROM participations
        JOIN players ON participations.player_id = players.id
        JOIN games ON participations.game_id = games.id
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()
    return data


def get_games():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date, player_count, winning_team
        FROM games
        ORDER BY id DESC
    """)

    games = cur.fetchall()

    cur.close()
    conn.close()
    return games


def get_game_details(game_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            players.name,
            participations.role,
            participations.won
        FROM participations
        JOIN players ON participations.player_id = players.id
        WHERE participations.game_id = %s
    """, (game_id,))

    data = cur.fetchall()

    cur.close()
    conn.close()
    return data


def delete_game(game_id):
    conn = get_connection()
    cur = conn.cursor()

    # Durch ON DELETE CASCADE werden participations automatisch gelöscht
    cur.execute(
        "DELETE FROM games WHERE id = %s",
        (game_id,)
    )

    conn.commit()
    cur.close()
    conn.close()


def load_dataframe():
    """
    Lädt alle Spiel-Teilnahmen als DataFrame.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            players.name AS player,
            participations.role,
            participations.won,
            games.player_count,
            games.winning_team,
            games.date,
            participations.game_id
        FROM participations
        JOIN players ON participations.player_id = players.id
        JOIN games ON participations.game_id = games.id
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "player",
        "role",
        "won",
        "player_count",
        "winning_team",
        "date",
        "game_id"
    ])

    df["date"] = pd.to_datetime(df["date"])
    return df