import datetime as dt
import streamlit as st
import pandas as pd
import sqlite3
from bbline.dashboard_data import get_dashboard_stats, get_profit_by_date
from bbline.utils import DB_PATH
from bbline.analysis.leakfinder import run_leakfinder, get_example_hands
from bbline.hands_table import fetch_hands_df
from bbline.replayer.replay_one import display_hand_replay

st.set_page_config(page_title="BBLine Poker", layout="wide")

# --- sidebar фильтры --------------------------------------------------------
st.sidebar.header("Фильтры")

# 1. диапазон дат
date_col1, date_col2 = st.sidebar.columns(2)
date_from = date_col1.date_input("c", value=dt.date(2025, 1, 1))
date_to = date_col2.date_input("по", value=dt.date.today())

# 2. лимиты (подтянем distinct из БД)
with sqlite3.connect(DB_PATH) as cx:
    limits = sorted({row[0] for row in cx.execute("SELECT DISTINCT limit_bb FROM hands")})
limit_sel = st.sidebar.multiselect("Лимиты (bb)", limits, default=limits)

# 3. позиции hero
positions = ["BB", "SB", "BTN", "CO", "MP", "EP"]
pos_sel = st.sidebar.multiselect("Позиции hero", positions, default=positions)

# --- main content ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🚨 LeakFinder", "📋 Список рук", "🂡 Реплеер"])

# Получаем hand_id из query_params для реплеера
query_hand_id = st.query_params.get("hand_id", None)

with tab1:
    # --- собираем стату ---------------------------------------------------------
    stats = get_dashboard_stats(
        date_from=str(date_from),
        date_to=str(date_to),
        limits=limit_sel,
        positions=pos_sel,
    )

    # --- вывод метрик / графики -------------------------------------------------
    st.title("BBLine Poker — Dashboard Overall")
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
    st.header("Динамика профита по датам")

    dates, profit_usd = get_profit_by_date(
        date_from=str(date_from),
        date_to=str(date_to),
        limits=limit_sel,
        positions=pos_sel,
    )

    if not dates:
        st.info("Нет рук под выбранные фильтры.")
    else:
        df = pd.DataFrame(
            {
                "Дата": dates,
                "Профит $": profit_usd,
            }
        )
        c1, c2 = st.columns(2)
        c1.line_chart(df.set_index("Дата")["Профит $"])

    # =========================
    # Debug (можно убрать)
    # =========================
    with st.expander("DEBUG: Все данные", expanded=False):
        st.write(stats)
        st.dataframe(df if "df" in locals() else None)

with tab2:
    st.header("🚨 LeakFinder Lite")

    # Получаем утечки с учетом фильтров
    leaks = run_leakfinder(
        date_from=str(date_from),
        date_to=str(date_to),
        limits=limit_sel,
        positions=pos_sel,
        save_tags=True,
    )

    if not leaks:
        st.success("Лики по выбранным фильтрам не найдены! GG 😎")
    else:
        # Создаем колонки для метрик
        cols = st.columns(len(leaks))

        # Выводим каждую утечку в отдельной колонке
        for i, lk in enumerate(leaks):
            with cols[i]:
                st.metric(
                    label=lk["name"],
                    value=f"{lk['value']}%",
                    delta=f"порог {lk['threshold']}%",
                    delta_color="inverse",
                )
                st.markdown(lk["explain"])
                show_examples = st.button(
                    f"Показать примеры ({lk['name']})", key=f"examples_{lk['name']}"
                )
                if show_examples:
                    examples = get_example_hands(lk["name"], n=5, order="loss")
                    if not examples:
                        st.info("Нет подходящих рук для примера.")
                    else:
                        st.markdown("**Примеры рук:**")
                        for ex in examples:
                            # Делаем Hand ID кликабельным для реплеера
                            st.markdown(
                                f"- [{ex['hand_id']}](?hand_id={ex['hand_id']}) — {ex['hero_net']}$"
                            )
                st.markdown("---")

        # Добавляем разделитель
        st.markdown("---")

        # TODO: Добавить визуализацию heat-map
        st.info("🔥 Heat-map в разработке...")

        # TODO: Добавить примеры рук
        st.info("🎮 Примеры рук в разработке...")

with tab3:
    st.header("📋 Список всех рук")
    hands_df = fetch_hands_df(
        date_from=str(date_from),
        date_to=str(date_to),
        limits=limit_sel,
        positions=pos_sel,
    )
    if not hands_df.empty:
        # Делаем HandID кликабельным в DataFrame
        hands_df["HandID"] = hands_df["HandID"].apply(lambda x: f"[{x}](?hand_id={x})")
        st.dataframe(hands_df, hide_index=True)
    else:
        st.info("Нет рук для отображения по выбранным фильтрам.")

with tab4:
    st.header("🂡 Реплеер раздач")
    # Получаем список всех hand_id для селектора
    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()
        all_hand_ids = [
            row[0]
            for row in cur.execute(
                "SELECT hand_id FROM hands ORDER BY datetime_utc DESC"
            ).fetchall()
        ]

    # Определяем выбранный hand_id: из query_params или из селектора
    if query_hand_id and query_hand_id in all_hand_ids:
        # Если hand_id пришел из URL, выбираем его в селекторе
        selected_hand_id_index = all_hand_ids.index(query_hand_id)
        selected_hand_id = st.selectbox(
            "Выбери раздачу", all_hand_ids, index=selected_hand_id_index, key="replayer_select_box"
        )
    else:
        # Иначе используем первый или None
        selected_hand_id = st.selectbox(
            "Выбери раздачу",
            all_hand_ids,
            index=0 if all_hand_ids else None,
            key="replayer_select_box",
        )

    if selected_hand_id:
        display_hand_replay(selected_hand_id)
    else:
        st.info("Выберите Hand ID для отображения раздачи.")
