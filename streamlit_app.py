from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import auth
from PIL import Image

from pipeline import build_master, write_excel

from datetime import date

today = date.today()
SEASON = str(today.year if today.month >= 7 else today.year - 1)

page_icon = "images/matchday_icon.png"

st.set_page_config(page_title="matchday", page_icon=page_icon, layout="wide")

# authentication setup
auth_container = st.container()
with auth_container:
    cols = st.columns([6, 2, 2])
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if not st.session_state.logged_in:
        # Guest view: show login / signup
        with cols[1]:
            if st.button("Login"):
                st.session_state.show_login = True
                st.session_state.show_signup = False
        with cols[2]:
            if st.button("Sign Up"):
                st.session_state.show_signup = True
                st.session_state.show_login = False
    else:
        # Logged-in view: greeting + logout
        with cols[1]:
            st.markdown(f"**Hello, {st.session_state.username}**")
        with cols[2]:
            if st.button("Logout"):
                st.session_state.clear()
                st.success("Logged out successfully")
                st.rerun()


# LOGIN FORM
if st.session_state.get("show_login", False):
    with st.container():
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Login"):
                user_id = auth.auth_user(username, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.show_login = False
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        with col2:
            if st.button("Cancel"):
                st.session_state.show_login = False

# SIGNUP FORM
if st.session_state.get("show_signup", False):
    with st.container():
        st.subheader("Create Account")
        new_user = st.text_input("New username", key="signup_user")
        new_pass = st.text_input("New password", type="password", key="signup_pass")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create Account"):
                if auth.create_user(new_user, new_pass):
                    st.success("Account created! You can now log in.")
                    st.session_state.show_signup = False
                else:
                    st.error("Username already exists")
        with col2:
            if st.button("Cancel"):
                st.session_state.show_signup = False


auth.init_user_db()


AX_BG = "#071421"
SEPARATOR_COLOR = "#ffffff"


def file_mtime(path):
    p = Path(path)
    if not p.exists():
        return 0
    return p.stat().st_mtime


@st.cache_data(show_spinner=False)
def load_master_xlsx(path, mtime):
    return pd.read_excel(path, sheet_name="MASTER")


@st.cache_data(show_spinner=False)
def compute_percentiles(df, metrics, group_col=None):
    out = df.copy()
    for m in metrics:
        if m not in out.columns:
            continue
        if group_col is None:
            out[m + "_pct"] = out[m].rank(pct=True) * 100
        else:
            out[m + "_pct"] = out.groupby(group_col)[m].rank(pct=True) * 100
    return out


def draw_radial(ax, labels, vals_0_1, colors, group_bounds):
    SEP_THIN, SEP_THICK = 1.4, 2.6
    inner_radius = 0.32
    outer_radius = inner_radius + 0.92
    inner_overlay = inner_radius + 0.05
    scale = outer_radius - inner_overlay
    theta_circle = np.linspace(0, 2 * np.pi, 720)

    vals = np.array(vals_0_1, dtype=float)
    VIS_MIN = 0.06
    vals_plot = np.where(vals > 0, np.maximum(vals, VIS_MIN), 0.0)

    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    width = 2 * np.pi / n

    ax.set_facecolor(AX_BG)
    ax.set_ylim(0, outer_radius + 0.22)

    ax.bar(angles, vals_plot * scale, width=width, bottom=inner_overlay, align="edge", color=colors, zorder=2)

    for ang in angles:
        ax.plot([ang, ang], [inner_overlay, outer_radius], linewidth=SEP_THIN, color=SEPARATOR_COLOR, zorder=3)

    for b in group_bounds:
        if b >= n:
            continue
        ang = angles[b]
        ax.plot([ang, ang], [inner_overlay, outer_radius], linewidth=SEP_THICK, color=SEPARATOR_COLOR, zorder=4)

    ax.plot(theta_circle, np.full_like(theta_circle, outer_radius), color=SEPARATOR_COLOR, linewidth=SEP_THICK, zorder=5, clip_on=False)
    ax.plot(theta_circle, np.full_like(theta_circle, inner_overlay), color=SEPARATOR_COLOR, linewidth=SEP_THICK, zorder=6, clip_on=False)

    for r in np.linspace(inner_overlay, outer_radius, 6)[1:-1]:
        ax.plot(theta_circle, np.full_like(theta_circle, r), color="white", linewidth=0.7, alpha=0.20, zorder=1)

    for ang, lab in zip(angles + width / 2, labels):
        t = ax.text(ang, outer_radius + 0.12, lab, ha="center", va="center", fontsize=9, fontweight="bold", color="white", zorder=10)
        t.set_path_effects([path_effects.Stroke(linewidth=2.0, foreground="black"), path_effects.Normal()])

    ax.set_xticks([])
    ax.set_thetagrids([])
    ax.set_yticklabels([])


def build_radial_figure(labels, vals_0_1, colors, group_bounds):
    fig = plt.figure(figsize=(7.4, 7.4), facecolor=AX_BG)
    ax = plt.subplot(111, polar=True)
    draw_radial(ax, labels, vals_0_1, colors, group_bounds)
    fig.patch.set_facecolor(AX_BG)
    fig.tight_layout(pad=1.0)
    return fig

def auth_page():
    st.title("Login")
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            user_id = auth.authenticate_user(username, password)
            if user_id:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password")
    with tab_signup:
        new_user = st.text_input("New Username", key="signup_user")
        new_pass = st.text_input("New Password", type="password", key="signup_pass")

        if st.button("Create Account"):
            if auth.create_user(new_user, new_pass):
                st.success("Account created! You can now log in.")
            else:
                st.error("Username already exists.")

st.image("images/matchday_logo.png", width=300)

st.title("English Premier League Scouting Dashboard")

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

xlsx_path = data_dir / f"premier_league_master_{SEASON}.xlsx"

mtime = file_mtime(xlsx_path)

if not xlsx_path.exists():
    try:
        with st.spinner("Fetching Premier League data"):
            frames = build_master(season=int(SEASON))
            write_excel(frames, xlsx_path)
    except Exception as e:
        st.error(str(e))
        if not xlsx_path.exists():
            st.stop()
    mtime = file_mtime(xlsx_path)

df = load_master_xlsx(str(xlsx_path), mtime)

updated = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S") if mtime else "unknown"
# st.caption(f"Data file: {xlsx_path.name} | Last updated: {updated}")

df = df.copy()
df["player_name"] = df["player_name"].fillna("")
df["team"] = df["team"].fillna("")
df["team_short"] = df["team_short"].fillna("")
df["position"] = df["position"].fillna("")

teams = sorted([t for t in df["team"].dropna().unique().tolist() if t != ""])

with st.sidebar:
    search = st.text_input("Search player")
    team_sel = st.selectbox("Club", options=["All"] + teams, index=0)
    position_filter = st.multiselect("Position", options=["GKP", "DEF", "MID", "FWD"], default=["GKP", "DEF", "MID", "FWD"])
    minutes_min = st.slider("Min minutes", min_value=0, max_value=4000, value=0, step=10)
    metric_sort = st.selectbox(
        "Sort",
        options=[
            "minutes",
            "goals",
            "assists",
            "xG",
            "xA",
            "shots",
            "key_passes",
            "influence",
            "creativity",
            "threat",
            "ict_index",
        ],
        index=0,
    )
    sort_desc = st.checkbox("Sort descending", value=True)

df = df[df["minutes"].fillna(0) >= minutes_min]
if position_filter:
    df = df[df["position"].isin(position_filter)]

if team_sel != "All":
    df_view = df[df["team"] == team_sel].copy()
else:
    df_view = df.copy()

if search.strip():
    mask = df_view["player_name"].str.contains(search.strip(), case=False, na=False)
    df_view = df_view[mask]

if metric_sort in df_view.columns:
    df_view = df_view.sort_values(metric_sort, ascending=not sort_desc, na_position="last")

display_cols = [
    "player_name",
    "team_short",
    "position",
    "minutes",
    "goals",
    "assists",
    "xG",
    "xA",
    "shots",
    "key_passes",
    "influence",
    "creativity",
    "threat",
    "ict_index",
]
display_cols = [c for c in display_cols if c in df_view.columns]

st.subheader("Database")
st.dataframe(df_view[display_cols], use_container_width=True, height=520)

st.subheader("Player Breakdown")
df_sel = df_view.copy().reset_index(drop=True)
if len(df_sel) == 0:
    st.info("No players match the current filters")
    st.stop()

id_col = "fpl_id" if "fpl_id" in df_sel.columns else ("understat_id" if "understat_id" in df_sel.columns else None)

labels = []
for _, r in df_sel.iterrows():
    pid = str(int(r[id_col])) if (id_col is not None and pd.notna(r.get(id_col))) else ""
    team_s = r.get("team_short", "")
    pos_s = r.get("position", "")
    name_s = r.get("player_name", "")
    parts = [name_s]
    if team_s:
        parts.append(f"({team_s})")
    if pos_s:
        parts.append(pos_s)
    if pid:
        parts.append(pid)
    labels.append(" ".join(parts).strip())

label_sel = st.selectbox("Select", options=labels, index=0)
sel_idx = labels.index(label_sel)
row = df_sel.iloc[sel_idx]
player_sel = row.get("player_name", "")

kpi_cols = st.columns(4)
kpis = [
    ("Club", row.get("team_short", "")),
    ("Pos", row.get("position", "")),
    ("Minutes", int(row.get("minutes", 0) if pd.notna(row.get("minutes", np.nan)) else 0)),
    ("Starts", int(row.get("starts", 0) if pd.notna(row.get("starts", np.nan)) else 0)),
]
for i, (label, val) in enumerate(kpis):
    kpi_cols[i].metric(label, val)

tabs = st.tabs(["Overview", "Percentiles", "Compare", "Raw"])

with tabs[0]:
    key_stats = [
        "goals",
        "assists",
        "xG",
        "xA",
        "shots",
        "key_passes",
        "clean_sheets",
        "saves",
        "influence",
        "creativity",
        "threat",
        "ict_index",
    ]
    key_stats = [s for s in key_stats if s in df_view.columns]
    sdata = pd.DataFrame({"metric": key_stats, "value": [row.get(s) for s in key_stats]})
    st.dataframe(sdata, use_container_width=True, hide_index=True)

with tabs[1]:
    metrics = ["goals_p90", "xG_p90", "shots_p90", "assists_p90", "xA_p90", "key_passes_p90", "influence", "creativity", "threat", "ict_index"]
    metrics = [m for m in metrics if m in df.columns]
    df_pct = compute_percentiles(df, metrics, group_col="position")

    if id_col is not None and id_col in df_pct.columns and pd.notna(row.get(id_col)):
        row_pct = df_pct[df_pct[id_col] == row.get(id_col)].iloc[0]
    else:
        row_pct = df_pct[df_pct["player_name"] == player_sel].iloc[0]

    labels_radial = [
        "G/90",
        "xG/90",
        "Sh/90",
        "A/90",
        "xA/90",
        "KP/90",
        "Inf",
        "Cre",
        "Thr",
        "ICT",
    ]

    pct_vals = []
    for m in ["goals_p90", "xG_p90", "shots_p90", "assists_p90", "xA_p90", "key_passes_p90", "influence", "creativity", "threat", "ict_index"]:
        if m in metrics:
            v = row_pct.get(m + "_pct")
            pct_vals.append(float(v) / 100.0 if pd.notna(v) else 0.0)
        else:
            pct_vals.append(0.0)

    colors = [
        "#f6a019",
        "#f6a019",
        "#f6a019",
        "#2aa7ff",
        "#2aa7ff",
        "#2aa7ff",
        "#1c6dd0",
        "#1c6dd0",
        "#1c6dd0",
        "#1c6dd0",
    ]

    group_bounds = [3, 6]

    st.markdown(f"**{player_sel}** · {row.get('team_short','')} · {row.get('position','')}")
    fig = build_radial_figure(labels_radial, pct_vals, colors, group_bounds)
    st.pyplot(fig, use_container_width=True)

    pct_table = pd.DataFrame(
        {
            "metric": ["goals_p90", "xG_p90", "shots_p90", "assists_p90", "xA_p90", "key_passes_p90", "influence", "creativity", "threat", "ict_index"],
            "percentile": [row_pct.get(m + "_pct") if m in metrics else np.nan for m in ["goals_p90", "xG_p90", "shots_p90", "assists_p90", "xA_p90", "key_passes_p90", "influence", "creativity", "threat", "ict_index"]],
            "value": [row.get(m) if m in df_view.columns else np.nan for m in ["goals_p90", "xG_p90", "shots_p90", "assists_p90", "xA_p90", "key_passes_p90", "influence", "creativity", "threat", "ict_index"]],
        }
    )
    st.dataframe(pct_table, use_container_width=True, hide_index=True)

with tabs[2]:
    compare_pool = df_view.copy()
    if id_col is not None and id_col in compare_pool.columns and pd.notna(row.get(id_col)):
        compare_pool = compare_pool[compare_pool[id_col] != row.get(id_col)]
    else:
        compare_pool = compare_pool[compare_pool["player_name"] != player_sel]
    df_cmp = compare_pool.copy().reset_index(drop=True)
    if len(df_cmp) == 0:
        st.info("No other players available to compare under current filters")
    else:
        cmp_labels = []
        for _, r2 in df_cmp.iterrows():
            pid2 = str(int(r2[id_col])) if (id_col is not None and id_col in df_cmp.columns and pd.notna(r2.get(id_col))) else ""
            team2 = r2.get("team_short", "")
            pos2 = r2.get("position", "")
            name2 = r2.get("player_name", "")
            parts2 = [name2]
            if team2:
                parts2.append(f"({team2})")
            if pos2:
                parts2.append(pos2)
            if pid2:
                parts2.append(pid2)
            cmp_labels.append(" ".join(parts2).strip())
        other_label = st.selectbox("Compare with", options=cmp_labels, index=0)
        row2 = df_cmp.iloc[cmp_labels.index(other_label)]
        other = row2.get("player_name", "")
        metrics_cmp = ["minutes", "goals", "assists", "xG", "xA", "shots", "key_passes", "influence", "creativity", "threat", "ict_index"]
        metrics_cmp = [m for m in metrics_cmp if m in df_view.columns]
        comp = pd.DataFrame({"metric": metrics_cmp, player_sel: [row.get(m) for m in metrics_cmp], other: [row2.get(m) for m in metrics_cmp]})
        st.dataframe(comp, use_container_width=True, hide_index=True)

with tabs[3]:
    st.json({k: (None if (pd.isna(v) if isinstance(v, float) else False) else v) for k, v in row.to_dict().items()})