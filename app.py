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
    df = load_dataframe()

    # --- Zeitfilter ---
    filter_type = st.selectbox("Zeitfilter", ["All time", "Seit Datum", "Letzte N Spiele"])
    if filter_type == "Seit Datum":
        date = st.date_input("Startdatum")
        df = df[df["date"] >= pd.Timestamp(date)]
    elif filter_type == "Letzte N Spiele":
        n = st.number_input("Letzte N Spiele", 1, 100, 10)
        last_games = df.drop_duplicates("game_id").sort_values("date", ascending=False).head(n)["game_id"]
        df = df[df["game_id"].isin(last_games)]
        
    df_stats = player_stats(df)
    if df_stats.empty:
        st.info("No existing games.")
        st.stop()
        
    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Stars Section ---
    all_star = df_stats.sort_values("winrate", ascending=False).iloc[0]
    almighty_adv = df_stats.sort_values("adv_rate", ascending=False).iloc[0]
    groofy_guard = df_stats.sort_values("guardian_rate", ascending=False).iloc[0]
    
    cols = st.columns(3)
    with cols[0]:
        st.markdown("***TDS All Star***")
        st.markdown(f"### {all_star['player']}")
        st.markdown(f"<h2 style='color:lightblue'>{all_star['winrate']*100:.1f}%</h2>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown("***Almighty Adventurer***")
        st.markdown(f"### {almighty_adv['player']}")
        st.markdown(f"<h2 style='color:olive'>{almighty_adv['adv_rate']*100:.1f}%</h2>", unsafe_allow_html=True)
    with cols[2]:
        st.markdown("***Groofy Guardian***")
        st.markdown(f"### {groofy_guard['player']}")
        st.markdown(f"<h2 style='color:purple'>{groofy_guard['guardian_rate']*100:.1f}%</h2>", unsafe_allow_html=True)
            
    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Sorted Stats for Charts ---
    df_stats_sorted = df_stats.sort_values("winrate", ascending=True)
    df_adv_sorted = df_stats.sort_values("adv_rate", ascending=True)
    df_guard_sorted = df_stats.sort_values("guardian_rate", ascending=True)
    
    # --- Total Winrate Chart ---
    with st.container():
        # Hintergrundfarbe für alle Kinder setzen
        st.markdown(
            """
            <style>
            .total_winrate_container > div {
                background-color: rgba(200,200,200,0.3);
                padding: 15px;
                border-radius: 10px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Wrapper-Klasse für Container
        st.markdown('<div class="total_winrate_container"></div>', unsafe_allow_html=True)

        # Inhalt normal einfügen
        st.subheader("Total Ranking")
        fig = go.Figure(go.Bar(
            y=df_stats_sorted["player"],
            x=df_stats_sorted["winrate"]*100,
            orientation="h",
            marker_color="lightblue",
            text=[f"{v*100:.1f}% ({n} Spiele)" for v, n in zip(df_stats_sorted["winrate"], df_stats_sorted["games"])],
            textposition="inside"
        ))
        fig.update_layout(
            xaxis_title="Total Winrate (%)",
            xaxis=dict(range=[0, 100]),
            yaxis_title="Spieler",
            margin=dict(l=100, r=50, t=20, b=50),
            height=50 + 30*len(df_stats_sorted)
        )
        st.plotly_chart(fig, use_container_width=True, key="total_ranking_chart")
    

    # --- Adventurer Winrate Chart ---
    st.subheader("Adventurer Ranking")
    fig_adv = go.Figure(go.Bar(
        y=df_adv_sorted["player"],
        x=df_adv_sorted["adv_rate"]*100,
        orientation="h",
        marker_color="olive",
        text=[f"{v*100:.1f}% ({n} Spiele)" for v, n in zip(df_adv_sorted["adv_rate"], df_adv_sorted["adv_games"])],
        textposition="inside"
    ))
    fig_adv.update_layout(
        xaxis_title="Adventurer Winrate (%)",
        xaxis=dict(range=[0, 100]),
        yaxis_title="Spieler",
        margin=dict(l=100, r=50, t=20, b=50),
        height=50 + 30*len(df_adv_sorted)
    )
    st.plotly_chart(fig_adv, use_container_width=True, key="adv_ranking_chart")

    # --- Guardian Winrate Chart ---
    st.subheader("Guardian Ranking")
    fig_guard = go.Figure(go.Bar(
        y=df_guard_sorted["player"],
        x=df_guard_sorted["guardian_rate"]*100,
        orientation="h",
        marker_color="purple",
        text=[f"{v*100:.1f}% ({n} Spiele)" for v, n in zip(df_guard_sorted["guardian_rate"], df_guard_sorted["guard_games"])],
        textposition="inside"
    ))
    fig_guard.update_layout(
        xaxis_title="Guardian Winrate (%)",
        xaxis=dict(range=[0, 100]),
        yaxis_title="Spieler",
        margin=dict(l=100, r=50, t=20, b=50),
        height=50 + 30*len(df_guard_sorted)
    )
    st.plotly_chart(fig_guard, use_container_width=True, key="guard_ranking_chart")

    # --- Single Player Analysis ---
    st.subheader("Single Player Analysis")
    player_sel = st.selectbox("Select Player", df_stats_sorted["player"].tolist())
    player_row = df_stats[df_stats["player"]==player_sel].iloc[0]

    st.write(f"**Games played:** {player_row['games']}") 
    cols = st.columns([1,1,1])
    with cols[0]:
        st.markdown("**Total Winrate**")        
        st.markdown(f"{int(player_row['winrate']*player_row['games'])}/{player_row['games']}")
        fig = go.Figure(go.Pie(
            labels=["Wins","Losses"],
            values=[player_row['winrate'], 1-player_row['winrate']],
            hole=0.5,
            marker=dict(colors=[colors["Total"], colors["Loss"]]),
            textinfo='percent+label'
        ))
        fig.update_layout(width=200,height=200,margin=dict(l=50,r=50,t=50,b=50), showlegend=False)
        st.plotly_chart(fig, use_container_width=False, key=f"single_total_{player_sel}")
    with cols[1]:
        st.markdown("**Adventurer Winrate**")        
        st.markdown(f"{int(player_row['adv_rate']*player_row['adv_games'])}/{player_row['adv_games']}")
        fig = go.Figure(go.Pie(
            labels=["Wins","Losses"],
            values=[player_row['adv_rate'], 1-player_row['adv_rate']],
            hole=0.5,
            marker=dict(colors=[colors["Adventurers"], colors["Loss"]]),
            textinfo='percent+label'
        ))
        fig.update_layout(width=200,height=200,margin=dict(l=50,r=50,t=50,b=50), showlegend=False)
        st.plotly_chart(fig, use_container_width=False, key=f"single_adv_{player_sel}")
    with cols[2]:
        st.markdown("**Guardian Winrate**")
        st.markdown(f"{int(player_row['guardian_rate']*player_row['guard_games'])}/{player_row['guard_games']}")
        fig = go.Figure(go.Pie(
            labels=["Wins","Losses"],
            values=[player_row['guardian_rate'], 1-player_row['guardian_rate']],
            hole=0.5,
            marker=dict(colors=[colors["Guardians"], colors["Loss"]]),
            textinfo='percent+label'
        ))
        fig.update_layout(width=200,height=200,margin=dict(l=50,r=50,t=50,b=50), showlegend=False)
        st.plotly_chart(fig, use_container_width=False, key=f"single_guard_{player_sel}")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Two-Player Analysis ---
    st.subheader("Player Team Analysis")
    df = load_dataframe()
    if df.empty:
        st.info("The Team Analysis Statistics will be calculated if a team played more than 3 games together.")
        st.stop()
    players_unique = df["player"].unique().tolist()
    player1 = st.selectbox("Player 1", players_unique)
    player2 = st.selectbox("Player 2", [p for p in players_unique if p != player1])
    
    combo_row = player_synergy(df, player1, player2)
    if combo_row:
        cols = st.columns([1,1,1])
        with cols[0]:
            st.markdown("**Team Total Winrate**")
            fig = go.Figure(go.Pie(
                labels=["Wins","Losses"],
                values=[combo_row['winrate'], 1-combo_row['winrate']],
                hole=0.5,
                marker=dict(colors=[colors["Total"], colors["Loss"]]),
                textinfo='percent+label'
            ))
            fig.update_layout(width=200,height=200,margin=dict(l=50,r=50,t=50,b=50), showlegend=False)
            st.plotly_chart(fig, use_container_width=False, key=f"team_total_{player1}_{player2}")
        with cols[1]:
            st.markdown("**Team Adventurer Winrate**")
            fig = go.Figure(go.Pie(
                labels=["Wins","Losses"],
                values=[combo_row['adv_rate'], 1-combo_row['adv_rate']],
                hole=0.5,
                marker=dict(colors=[colors["Adventurers"], colors["Loss"]]),
                textinfo='percent+label'
            ))
            fig.update_layout(width=200,height=200,margin=dict(l=50,r=50,t=50,b=50), showlegend=False)
            st.plotly_chart(fig, use_container_width=False, key=f"team_adv_{player1}_{player2}")
        with cols[2]:
            st.markdown("**Team Guardian Winrate**")
            fig = go.Figure(go.Pie(
                labels=["Wins","Losses"],
                values=[combo_row['guardian_rate'], 1-combo_row['guardian_rate']],
                hole=0.5,
                marker=dict(colors=[colors["Guardians"], colors["Loss"]]),
                textinfo='percent+label'
            ))
            fig.update_layout(width=200,height=200,margin=dict(l=50,r=50,t=50,b=50), showlegend=False)
            st.plotly_chart(fig, use_container_width=False, key=f"team_guard_{player1}_{player2}")
    else:
        st.info(f"No games with {player1} and {player2} found.")
        
    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Top N Spielerpaare ---
    st.subheader("Top Teams")
    st.markdown("Only Teams with at least 3 games together will appear in the statistic.")
    df_pairs = top_player_synergies(df, top_n=20, min_games=3)
    
    if not df_pairs.empty:
        df_pairs_display = df_pairs.rename(columns={
            "player1": "Player 1",
            "player2": "Player 2",
            "games": "Games Together",
            "winrate": "Team Total Winrate",
            "adv_rate": "Team Adventurer Winrate",
            "guardian_rate": "Team Guardian Winrate"
        })
        st.dataframe(
            df_pairs_display.reset_index(drop=True).style.format({
                "Team Total Winrate": "{:.1%}",
                "Team Adventurer Winrate": "{:.1%}",
                "Team Guardian Winrate": "{:.1%}"
            })
        )
    else:
        st.info("No teams found with at least 3 games together.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Spielauswertung horizontal ---
    st.subheader("Wins by number of players (%)")
    pivot = prepare_playercount_percentage(df)
    
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
    st.plotly_chart(fig, key="playercount_win_chart")

# -----------------------------
# GAME HISTORY
# -----------------------------
elif menu == "Game History":
    st.header("Game History")
    games = get_games()
    if not games:
        st.info("No existing Games")
        st.stop()

    # Session-State für gelöschte Spiele
    if "deleted_games" not in st.session_state:
        st.session_state.deleted_games = set()

    for g in games:
        game_id, date, player_count, winning_team = g

        # Überspringe bereits gelöschte Spiele
        if game_id in st.session_state.deleted_games:
            continue

        with st.expander(f"Game {game_id} | {player_count} Players | Winning Team: {winning_team} | {pd.to_datetime(date)}"):
            df_game = pd.DataFrame(get_game_details(game_id), columns=["Player", "Role", "Won"])
            st.table(df_game)

            # Delete-Button
            button_key = f"delete{game_id}"
            if st.button("Delete Game", key=button_key):
                delete_game(game_id)
                st.session_state.deleted_games.add(game_id)
                st.warning(f"Game {game_id} deleted")