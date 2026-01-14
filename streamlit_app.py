from pathlib import Path
import streamlit as st

ICON = Path(__file__).parent / "images" / "matchday_icon.png"
LOGO = Path(__file__).parent / "images" / "matchday_logo.png"

st.set_page_config(page_title="Matchday", page_icon=str(ICON), layout="wide")

st.image(str(LOGO), use_container_width=True)

st.title("English Premier League Scouting Dashboard")
# st.write(
#     "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
# )

st.write(
    "cant rush greatness"
)