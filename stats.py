# stats.py
import pandas as pd
from itertools import combinations
from models import get_all_participations, load_dataframe


# ----------------------------------
# ALTE DATEN HIER EINTRAGEN
# ----------------------------------
# Format:
# player, adv_games, adv_wins, guard_games, guard_wins

legacy_stats = pd.DataFrame([
    
    # Beispiel:
    {"player":"Fiori", "adv_games":3, "adv_wins":1, "guard_games":4, "guard_wins":4},
    {"player":"Tiuri","adv_games":6,"adv_wins":2,"guard_games":8,"guard_wins":6},
    {"player":"Estragon", "adv_games":5, "adv_wins":2, "guard_games":4, "guard_wins":3},
    {"player":"Lima","adv_games":7,"adv_wins":2,"guard_games":4,"guard_wins":4},
    {"player":"Grizzly", "adv_games":9, "adv_wins":2, "guard_games":2, "guard_wins":2},
    {"player":"Squirrel","adv_games":5,"adv_wins":0,"guard_games":2,"guard_wins":2},
    {"player":"Fäntu", "adv_games":6, "adv_wins":0, "guard_games":3, "guard_wins":2},
    {"player":"Galilea","adv_games":11,"adv_wins":3,"guard_games":3,"guard_wins":2},
    {"player":"Arisca", "adv_games":10, "adv_wins":2, "guard_games":0, "guard_wins":0},
    {"player":"Bohne", "adv_games":7, "adv_wins":3, "guard_games":3, "guard_wins":3},
    {"player":"Robbe","adv_games":4,"adv_wins":1,"guard_games":3,"guard_wins":3},
    {"player":"Keck", "adv_games":3, "adv_wins":1, "guard_games":2, "guard_wins":0},
    {"player":"Fresco","adv_games":1,"adv_wins":0,"guard_games":1,"guard_wins":0},
    {"player":"Coccinelle", "adv_games":2, "adv_wins":1, "guard_games":0, "guard_wins":0},

])

# ----------------------------------
# PLAYER STATS
# ----------------------------------
def player_stats(df):

    players = set()

    if not df.empty:
        players.update(df["player"].unique())

    if not legacy_stats.empty:
        players.update(legacy_stats["player"].unique())

    rows = []

    for player in players:

        # -------------------------
        # NEUE SPIELE AUS DER DB
        # -------------------------

        if not df.empty:

            p = df[df["player"] == player]

            adv = p[p["role"] == "Adventurer"]
            guard = p[p["role"] == "Guardian"]

            adv_games_new = len(adv)
            adv_wins_new = adv["won"].sum()

            guard_games_new = len(guard)
            guard_wins_new = guard["won"].sum()

        else:

            adv_games_new = 0
            adv_wins_new = 0
            guard_games_new = 0
            guard_wins_new = 0


        # -------------------------
        # ALTE DATEN
        # -------------------------

        legacy_row = legacy_stats[legacy_stats["player"] == player]

        if not legacy_row.empty:

            adv_games_old = int(legacy_row["adv_games"].iloc[0])
            adv_wins_old = int(legacy_row["adv_wins"].iloc[0])
            guard_games_old = int(legacy_row["guard_games"].iloc[0])
            guard_wins_old = int(legacy_row["guard_wins"].iloc[0])

        else:

            adv_games_old = 0
            adv_wins_old = 0
            guard_games_old = 0
            guard_wins_old = 0


        # -------------------------
        # KOMBINIEREN
        # -------------------------

        adv_games = adv_games_new + adv_games_old
        adv_wins = adv_wins_new + adv_wins_old

        guard_games = guard_games_new + guard_games_old
        guard_wins = guard_wins_new + guard_wins_old

        total_games = adv_games + guard_games
        total_wins = adv_wins + guard_wins


        # -------------------------
        # WINRATES
        # -------------------------

        winrate = total_wins / total_games if total_games else 0
        adv_rate = adv_wins / adv_games if adv_games else 0
        guardian_rate = guard_wins / guard_games if guard_games else 0


        rows.append({
            "player": player,
            "games": total_games,
            "adv_games": adv_games,
            "guard_games": guard_games,
            "winrate": winrate,
            "adv_rate": adv_rate,
            "guardian_rate": guardian_rate
        })

    return pd.DataFrame(rows).sort_values("winrate", ascending=False)

# -----------------------------
# TEAM STATS
# -----------------------------
def team_stats(df):
    if df.empty:
        return None
    team = df.groupby("winning_team")["game_id"].nunique()
    return team

# -----------------------------
# WINS BY PLAYER COUNT
# -----------------------------
def playercount_game_results(df):
    if df.empty:
        return pd.DataFrame()

    # pro Spiel einmal zählen
    games = df.drop_duplicates(subset=["game_id"])
    result = games.groupby(["player_count","winning_team"]).size().reset_index(name="wins")
    totals = games.groupby("player_count").size().reset_index(name="total")
    merged = result.merge(totals, on="player_count")
    merged["percentage"] = merged["wins"] / merged["total"] * 100
    return merged

# -----------------------------
# PLAYER SYNERGIES
# -----------------------------
def player_synergies(df):
    if df.empty:
        return pd.DataFrame()

    results = []
    games = df.groupby("game_id")
    for game_id, g in games:
        players = g["player"].tolist()
        for p1, p2 in combinations(players, 2):
            sub = g[g["player"].isin([p1, p2])]
            both_won = sub["won"].sum() == 2
            results.append({
                "player1": p1,
                "player2": p2,
                "both_won": both_won,
                "game_id": game_id
            })

    sdf = pd.DataFrame(results)
    stats = (
        sdf.groupby(["player1","player2"])
        .agg(games=("game_id","count"), wins=("both_won","sum"))
        .reset_index()
    )
    stats["winrate"] = stats["wins"] / stats["games"]
    return stats


# -----------------------------
# PLAYER SYNERGY (ein Paar)
# -----------------------------
def player_synergy(df, player1, player2):

    if df.empty:
        return None

    # Spiele finden, in denen beide vorkommen
    game_counts = df[df["player"].isin([player1, player2])].groupby("game_id")["player"].nunique()
    games_both = game_counts[game_counts == 2].index
    if len(games_both) == 0:
        return None

    combo_df = df[df["game_id"].isin(games_both)]

    total_games = 0
    total_wins = 0
    adv_games = adv_wins = 0
    guard_games = guard_wins = 0

    for game_id in games_both:

        g = combo_df[combo_df["game_id"] == game_id].set_index("player")

        role1 = g.loc[player1, "role"]
        role2 = g.loc[player2, "role"]

        won1 = g.loc[player1, "won"]
        won2 = g.loc[player2, "won"]

        # nur Spiele zählen wenn gleiche Rolle
        if role1 != role2:
            continue

        total_games += 1

        if won1 and won2:
            total_wins += 1

        if role1 == "Adventurer":
            adv_games += 1
            if won1 and won2:
                adv_wins += 1

        if role1 == "Guardian":
            guard_games += 1
            if won1 and won2:
                guard_wins += 1

    if total_games == 0:
        return None

    return {
        "winrate": total_wins / total_games,
        "adv_rate": adv_wins / adv_games if adv_games else 0,
        "guardian_rate": guard_wins / guard_games if guard_games else 0,
        "games": total_games
    }

# -----------------------------
# TOP PLAYER SYNERGIES
# -----------------------------
def top_player_synergies(df, top_n=10, min_games=3):
    """
    Liefert die erfolgreichsten Spielerpaare (Top N),
    sortiert nach Gesamt-Winrate.
    min_games: nur Paare mit mindestens dieser Anzahl gemeinsamer Spiele
    """
    if df.empty:
        return pd.DataFrame(columns=["player1","player2","games","winrate","adv_rate","guardian_rate"])

    players = df["player"].unique()
    results = []

    for p1, p2 in combinations(players, 2):
        res = player_synergy(df, p1, p2)
        if res and res["games"] >= min_games:
            results.append({
                "player1": p1,
                "player2": p2,
                "games": res["games"],
                "winrate": res["winrate"],
                "adv_rate": res["adv_rate"],
                "guardian_rate": res["guardian_rate"]
            })

    if not results:
        return pd.DataFrame(columns=["player1","player2","games","winrate","adv_rate","guardian_rate"])

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("winrate", ascending=False).head(top_n)
    return df_results
# -----------------------------
# ADVENTURER TEAM IMPACT
# -----------------------------
def role_team_effect(df, player, role):
    """
    Berechnet den Einfluss eines Spielers, wenn er in einer bestimmten Rolle spielt.
    Gibt den Anteil der Spiele zurück, die das Team der Rolle gewonnen hat.
    role: "Adventurer" oder "Guardian"
    """
    if df.empty or role not in ["Adventurer","Guardian"]:
        return 0

    subset = df[(df["player"] == player) & (df["role"] == role)]
    games = subset["game_id"].unique()
    if len(games) == 0:
        return 0

    games_df = df[df["game_id"].isin(games)].drop_duplicates("game_id")
    if role == "Adventurer":
        wins = (games_df["winning_team"] == "Adventurers").sum()
    else:
        wins = (games_df["winning_team"] == "Guardians").sum()

    return wins / len(games_df)


def prepare_playercount_percentage(df):
    """
    Aggregiert pro Spieleranzahl die Siege der Teams als Prozent.
    Zusätzlich liefert die absolute Anzahl Siege pro Team.
    Berücksichtigt alte/legacy Daten.
    Gibt ein Pivot-DataFrame zurück mit Spalten:
    - Adventurers (Prozent)
    - Guardians (Prozent)
    - Adventurers_wins (absolute Zahl)
    - Guardians_wins (absolute Zahl)
    - total_games (absolute Zahl)
    """

    # Legacy-Daten
    legacy = {
        6: {"total": 1, "Adventurers": 1, "Guardians": 0},
        7: {"total": 8, "Adventurers": 4, "Guardians": 4},
        8: {"total": 2, "Adventurers": 2, "Guardians": 0},
        10: {"total": 5, "Adventurers": 0, "Guardians": 5},
    }

    # --- aktuelle Spiele aggregieren ---
    if df.empty:
        games_df = pd.DataFrame(columns=["player_count", "winning_team", "wins"])
    else:
        games = df.drop_duplicates(subset=["game_id"])
        agg = games.groupby(["player_count","winning_team"]).size().reset_index(name="wins")
        games_df = agg

    # --- Legacy-Daten ergänzen ---
    for pc, stats in legacy.items():
        for team in ["Adventurers","Guardians"]:
            wins = stats[team]
            # Prüfen, ob schon ein Eintrag existiert
            if not ((games_df["player_count"]==pc) & (games_df["winning_team"]==team)).any():
                games_df = pd.concat([games_df, pd.DataFrame([{
                    "player_count": pc,
                    "winning_team": team,
                    "wins": wins
                }])], ignore_index=True)

    # --- Alle Spielerzahlen sammeln (Legacy + aktuelle) ---
    all_player_counts = sorted(set(list(games_df["player_count"].astype(int)) + list(legacy.keys())))
    total_games_df = pd.DataFrame(index=all_player_counts)
    total_games_df.index.name = "player_count"

    # Spalten initialisieren
    total_games_df["total_games"] = 0
    total_games_df["Adventurers"] = 0
    total_games_df["Guardians"] = 0
    total_games_df["Adventurers_wins"] = 0
    total_games_df["Guardians_wins"] = 0

    # --- Werte eintragen ---
    for pc in all_player_counts:
        subset = games_df[games_df["player_count"]==pc]
        total = subset["wins"].sum()
        total_games_df.at[pc, "total_games"] = total

        for team in ["Adventurers","Guardians"]:
            wins = subset[subset["winning_team"]==team]["wins"].sum()
            total_games_df.at[pc, f"{team}_wins"] = wins
            total_games_df.at[pc, team] = (wins / total * 100) if total>0 else 0

    return total_games_df.sort_index()