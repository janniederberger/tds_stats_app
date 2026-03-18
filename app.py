import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from models import *
from stats import *
from database import init_db

# --- DB initialisieren ---
init_db()
st.set_page_config(layout="wide")
st.title("TDS Statistics")

colors = {"Total":"lightblue","Adventurers":"olive","Guardians":"purple","Loss":"lightgray"}

# Sidebar Menu
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Player", "Log Game", "Game History"])

# -----------------------------
# ADD PLAYER
# -----------------------------
if menu == "Add Player":
    st.header("Add Player")
    name = st.text_input("Name")
    if st.button("Add"):
        add_player(name)
        st.success(f"Player '{name}' added!")
    st.subheader("Existing Players")
    for pid, pname in get_players():
        st.write(pname)

# -----------------------------
# LOG GAME
# -----------------------------
elif menu == "Log Game":
    st.header("Log New Game")
    players = get_players()
    if not players:
        st.warning("Add players first!")
        st.stop()

    player_dict = {name: pid for pid, name in players}

    selected_players = st.multiselect(
        "Players in this game:",
        list(player_dict.keys())
    )

    if len(selected_players) < 4:
        st.warning("Add at least 4 players to the game")
        st.stop()

    player_count = len(selected_players)
    winning_team = st.selectbox("Winning Team", ["Guardians", "Adventurers"])

    st.subheader("Player Roles")
    roles = {}
    for p in selected_players:
        roles[p] = st.selectbox(f"{p} Role", ["Guardian", "Adventurer"], key=f"role_{p}")

    if st.button("Save Game"):
        game_id = add_game(player_count, winning_team)
        for player_name in selected_players:
            pid = player_dict[player_name]
            role = roles[player_name]
            won = (role == "Adventurer" and winning_team == "Adventurers") or \
                  (role == "Guardian" and winning_team == "Guardians")
            add_participation(game_id, pid, role, won)
        st.success(f"Game ({player_count} Player, Winning Team: {winning_team}) gespeichert!")

# -----------------------------
# DASHBOARD
# -----------------------------
elif menu == "Dashboard":
    st.header("Dashboard")

    # --- Daten einmal laden ---
    @st.cache_data
    def load_all_data():
        return load_dataframe()  # unverändert, nur einmal aus DB

    df = load_all_data()
    if df.empty:
        st.info("Keine Spiele eingetragen.")
        st.stop()

    # --- Spielerstatistiken cachen ---
    @st.cache_data
    def get_stats(df_cached):
        return player_stats(df_cached)  # originale Funktion

    df_stats = get_stats(df)
    if df_stats.empty:
        st.info("No existing games.")
        st.stop()

    # Stars Section unverändert
    all_star = df_stats.sort_values("winrate", ascending=False).iloc[0]
    almighty_adv = df_stats.sort_values("adv_rate", ascending=False).iloc[0]
    groofy_guard = df_stats.sort_values("guardian_rate", ascending=False).iloc[0]

    # Charts vorbereiten
    df_stats_sorted = df_stats.sort_values("winrate", ascending=True)
    df_adv_sorted = df_stats.sort_values("adv_rate", ascending=True)
    df_guard_sorted = df_stats.sort_values("guardian_rate", ascending=True)

    # Total, Adventurer, Guardian Charts wie vorher (keine Änderung)

    # --- Single Player Analysis ---
    player_sel = st.selectbox("Select Player", df_stats_sorted["player"].tolist())
    player_row = df_stats[df_stats["player"]==player_sel].iloc[0]

    # Pie-Charts für Player Analysis
    def plot_player_pie(win_rate, total_games, color):
        fig = go.Figure(go.Pie(
            labels=["Wins","Losses"],
            values=[win_rate*total_games, total_games - win_rate*total_games],
            hole=0.5,
            marker=dict(colors=[color, colors["Loss"]]),
            textinfo='percent+label'
        ))
        fig.update_layout(width=200,height=200,margin=dict(l=50,r=50,t=50,b=50), showlegend=False)
        st.plotly_chart(fig, use_container_width=False)

    cols = st.columns([1,1,1])
    with cols[0]:
        plot_player_pie(player_row['winrate'], player_row['games'], colors["Total"])
    with cols[1]:
        plot_player_pie(player_row['adv_rate'], player_row['adv_games'], colors["Adventurers"])
    with cols[2]:
        plot_player_pie(player_row['guardian_rate'], player_row['guard_games'], colors["Guardians"])

    # --- Player Team Analysis ---
    @st.cache_data
    def get_team_stats(df_cached, p1, p2):
        return player_synergy(df_cached, p1, p2)

    players_unique = df["player"].unique().tolist()
    player1 = st.selectbox("Player 1", players_unique)
    player2 = st.selectbox("Player 2", [p for p in players_unique if p != player1])

    combo_row = get_team_stats(df, player1, player2)
    if combo_row:
        cols = st.columns([1,1,1])
        with cols[0]:
            plot_player_pie(combo_row['winrate'], 1, colors["Total"])
        with cols[1]:
            plot_player_pie(combo_row['adv_rate'], 1, colors["Adventurers"])
        with cols[2]:
            plot_player_pie(combo_row['guardian_rate'], 1, colors["Guardians"])
    else:
        st.info(f"No games with {player1} and {player2} found.")

    # --- Top Teams ---
    st.subheader("Top Teams")
    @st.cache_data
    def get_top_pairs(df_cached):
        return top_player_synergies(df_cached, top_n=20, min_games=3)

    df_pairs = get_top_pairs(df)
    if not df_pairs.empty:
        df_pairs_display = df_pairs.rename(columns={
            "player1": "Player 1",
            "player2": "Player 2",
            "games": "Games Together",
            "winrate": "Team Total Winrate",
            "adv_rate": "Team Adventurer Winrate",
            "guardian_rate": "Team Guardian Winrate"
        })
        st.dataframe(df_pairs_display.reset_index(drop=True).style.format({
            "Team Total Winrate": "{:.1%}",
            "Team Adventurer Winrate": "{:.1%}",
            "Team Guardian Winrate": "{:.1%}"
        }))
    else:
        st.info("No teams found with at least 3 games together.")

    # --- Wins by Number of Players ---
    st.subheader("Wins by number of players (%)")
    @st.cache_data
    def prepare_playercount(df_cached):
        return prepare_playercount_percentage(df_cached)

    pivot = prepare_playercount(df)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=pivot.index.astype(str),
        x=pivot["Adventurers"],
        name="Adventurers",
        orientation="h",
        text=[f"{p:.0f}% ({w}/{t})" for p, w, t in zip(pivot["Adventurers"], pivot["Adventurers_wins"], pivot["total_games"])],
        textposition="inside",
        marker_color=colors["Adventurers"]
    ))
    fig.add_trace(go.Bar(
        y=pivot.index.astype(str),
        x=pivot["Guardians"],
        name="Guardians",
        orientation="h",
        text=[f"{p:.0f}% ({w}/{t})" for p, w, t in zip(pivot["Guardians"], pivot["Guardians_wins"], pivot["total_games"])],
        textposition="inside",
        marker_color=colors["Guardians"]
    ))
    fig.update_layout(
        barmode="stack",
        xaxis_title="Percentage",
        yaxis_title="Number of Players",
        yaxis=dict(categoryorder='array', categoryarray=sorted(pivot.index.astype(int))),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig)

# -----------------------------
# GAME HISTORY
# -----------------------------
elif menu == "Game History":
    st.header("Game History")
    games = get_games()
    if not games:
        st.info("No existing Games")
        st.stop()
    for g in games:
        game_id, date, player_count, winning_team = g
        with st.expander(f"Game {game_id} | {player_count} Players | Winning Team: {winning_team} | {pd.to_datetime(date)}"):
            df_game = pd.DataFrame(get_game_details(game_id), columns=["Player","Role","Won"])
            st.table(df_game)
            if st.button("Delete Game", key=f"delete{game_id}"):
                delete_game(game_id)
                st.warning(f"Game {game_id} deleted")
                st.experimental_rerun()