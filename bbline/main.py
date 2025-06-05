import streamlit as st
from dashboard_data import get_dashboard_stats, get_profit_by_date

st.set_page_config(
    page_title="BBLine Poker Dashboard",
    layout="wide",
)

st.title("BBLine Poker — Dashboard Overall")

# =========================
# Основные метрики HERO
# =========================

stats = get_dashboard_stats()

cols = st.columns(6)
cols[0].metric("Рук сыграно", stats["Hands"])
cols[1].metric("Профит $", stats["Profit $"])
cols[2].metric("Профит (bb)", stats["Profit bb"])
cols[3].metric("bb/100", stats["TBB/100"])
cols[4].metric("Rake $", stats["Hero Rake $"])
cols[5].metric("VPIP %", stats["VPIP"])

cols2 = st.columns(5)
cols2[0].metric("PFR %", stats["PFR"])
cols2[1].metric("WtS %", stats["WtS"])
cols2[2].metric("WaS %", stats["WaS"])
cols2[3].metric("WwS %", stats["WwS"])
cols2[4].metric("WWSF %", stats["WWSF"])

st.markdown("---")

# =========================
# Графики по датам
# =========================

st.header("Динамика профита по датам")

data = get_profit_by_date()
if not data:
    st.info("Нет данных для графика. Импортируй хэнды — и будет кайф.")
else:
    import pandas as pd

    df = pd.DataFrame(data, columns=["Дата", "Профит $", "Профит bb"])
    df["Дата"] = pd.to_datetime(df["Дата"])

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Профит $")
        st.line_chart(df.set_index("Дата")["Профит $"])
    with col_g2:
        st.subheader("Профит bb")
        st.line_chart(df.set_index("Дата")["Профит bb"])

st.markdown("---")

# =========================
# Debug (можно убрать)
# =========================
with st.expander("DEBUG: Все данные", expanded=False):
    st.write(stats)
    st.dataframe(df if "df" in locals() else None)
