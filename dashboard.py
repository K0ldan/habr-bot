import io
import json
import os
import duckdb
import pandas as pd
import sentry_sdk
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SENTRY_DSN = os.getenv("SENTRY_DSN")
if not SENTRY_DSN and hasattr(st, "secrets") and "SENTRY_DSN" in st.secrets:
    SENTRY_DSN = st.secrets["SENTRY_DSN"]

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
    )

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
if not TURSO_DATABASE_URL and hasattr(st, "secrets") and "TURSO_DATABASE_URL" in st.secrets:
    TURSO_DATABASE_URL = st.secrets["TURSO_DATABASE_URL"]

TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
if not TURSO_AUTH_TOKEN and hasattr(st, "secrets") and "TURSO_AUTH_TOKEN" in st.secrets:
    TURSO_AUTH_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]

# Настройка страницы
st.set_page_config(
    page_title="Habr Data & ML Radar",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Пользовательские стили для красивой типографики и карточек
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 10px;
    }
    .badge-senior { background-color: #ff4b4b; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; font-size: 12px; }
    .badge-middle { background-color: #ffa421; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; font-size: 12px; }
    .badge-junior { background-color: #21c354; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; font-size: 12px; }
    .badge-hub { background-color: #1f77b4; color: white; padding: 3px 8px; border-radius: 5px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 1. Загрузка данных
# ==========================================
@st.cache_data(ttl=30)
def load_data():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        import libsql_client
        target_url = TURSO_DATABASE_URL.replace("libsql://", "https://") if TURSO_DATABASE_URL.startswith("libsql://") else TURSO_DATABASE_URL
        client = libsql_client.create_client_sync(url=target_url, auth_token=TURSO_AUTH_TOKEN)
        try:
            res = client.execute("SELECT url, title, hub, difficulty, article_type, tech_stack, summary, created_at FROM articles ORDER BY created_at DESC")
            columns = ["url", "title", "hub", "difficulty", "article_type", "tech_stack", "summary", "created_at"]
            data = [list(row) for row in res.rows]
            df = pd.DataFrame(data, columns=columns)
        finally:
            client.close()
    elif os.path.exists("articles.db"):
        import sqlite3
        conn = sqlite3.connect("articles.db")
        df = pd.read_sql("SELECT * FROM articles ORDER BY created_at DESC", conn)
        conn.close()
    else:
        df = pd.DataFrame(columns=["url", "title", "hub", "difficulty", "article_type", "tech_stack", "summary", "created_at"])

    # Распаковываем JSON-массив технологий
    def parse_stack(val):
        if not val:
            return []
        try:
            items = json.loads(val) if isinstance(val, str) else val
            return [str(x).strip() for x in items if x]
        except Exception:
            return []

    df["tech_list"] = df["tech_stack"].apply(parse_stack)
    df["difficulty"] = df["difficulty"].fillna("Middle").replace({"Unknown": "Middle", "": "Middle"})
    df["article_type"] = df["article_type"].fillna("Кейс").replace({"Article": "Кейс", "": "Кейс"})
    return df


df = load_data()


# ==========================================
# 2. DuckDB Аналитика (In-Memory)
# ==========================================
con = duckdb.connect(database=":memory:")
con.register("articles", df)

# Статистика популярных технологий
if not df.empty and df["tech_list"].apply(len).sum() > 0:
    tech_stats = con.execute("""
        SELECT 
            unnest(tech_list) as "Технология", 
            count(*) as "Упоминаний"
        FROM articles
        WHERE length(tech_stack) > 2
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 12
    """).df()
else:
    tech_stats = pd.DataFrame(columns=["Технология", "Упоминаний"])

# Статистика по уровням сложности
if not df.empty:
    diff_stats = con.execute("""
        SELECT 
            difficulty as "Уровень", 
            count(*) as "Количество"
        FROM articles
        WHERE difficulty IN ('Junior', 'Middle', 'Senior', 'Lead')
        GROUP BY 1
        ORDER BY 2 DESC
    """).df()
else:
    diff_stats = pd.DataFrame(columns=["Уровень", "Количество"])


# ==========================================
# 3. Боковая панель: Фильтры поиска
# ==========================================
with st.sidebar:
    st.image("https://habr.com/img/habr_logo_ru.svg", width=120)
    st.title("Фильтры ленты")
    st.markdown("Настройте выдачу статей под свои интересы:")

    selected_hub = st.radio(
        "Направление:",
        ["Все направления", "Data Engineering", "Machine Learning"],
        index=0
    )

    selected_diff = st.multiselect(
        "Уровень сложности:",
        ["Junior", "Middle", "Senior", "Lead"],
        default=[]
    )

    search_query = st.text_input("🔍 Поиск по стеку или названию:", placeholder="например: Kafka или PyTorch")

    st.markdown("---")
    st.markdown("💡 **О проекте:**")
    st.caption("Платформа автоматически собирает статьи с Хабра 4 раза в день, проводит анализ через модель Qwen и сохраняет структурированные данные в облако Turso.")


# ==========================================
# 4. Главная область: Вкладки
# ==========================================
st.title("🧠 Data & ML Engineering Radar")
st.markdown("Интеллектуальный дайджест и радар актуальных технологий на основе публикаций Хабра.")

tab_feed, tab_analytics, tab_export = st.tabs([
    "📑 Лента выжимок", 
    "📊 Аналитика и Тренды", 
    "📦 Экспорт в Data Lake (Parquet)"
])


# ------------------------------------------
# ВКЛАДКА 1: Читабельная лента статей
# ------------------------------------------
with tab_feed:
    # Применяем фильтры
    filtered_df = df.copy()

    if selected_hub != "Все направления":
        filtered_df = filtered_df[filtered_df["hub"] == selected_hub]

    if selected_diff:
        filtered_df = filtered_df[filtered_df["difficulty"].isin(selected_diff)]

    if search_query:
        query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["title"].str.lower().str.contains(query) |
            filtered_df["summary"].str.lower().str.contains(query) |
            filtered_df["tech_list"].apply(lambda tags: any(query in t.lower() for t in tags))
        ]

    st.subheader(f"Найдено материалов: {len(filtered_df)}")

    if filtered_df.empty:
        st.info("По выбранным фильтрам статей не найдено. Попробуйте сбросить фильтры слева.")
    else:
        for idx, row in filtered_df.iterrows():
            diff = row["difficulty"]
            badge_class = "badge-senior" if diff == "Senior" else ("badge-middle" if diff == "Middle" else "badge-junior")

            with st.container():
                st.markdown(f"""
                <div style="border: 1px solid #e6e9ef; border-radius: 8px; padding: 18px; margin-bottom: 16px; background-color: white;">
                    <div style="margin-bottom: 8px;">
                        <span class="badge-hub">{row['hub']}</span>
                        <span class="{badge_class}">{diff}</span>
                        <span style="color: #6c757d; font-size: 13px; margin-left: 10px;">Формат: <b>{row['article_type']}</b></span>
                    </div>
                    <h3 style="margin-top: 4px; margin-bottom: 10px;">
                        <a href="{row['url']}" target="_blank" style="text-decoration: none; color: #1e1e1e;">{row['title']}</a>
                    </h3>
                </div>
                """, unsafe_allow_html=True)

                # Выжимка
                if row["summary"]:
                    st.markdown(row["summary"], unsafe_allow_html=True)

                # Теги технологий
                if row["tech_list"]:
                    tag_pills = " ".join([f"`#{t}`" for t in row["tech_list"]])
                    st.markdown(f"**Стек:** {tag_pills}")

                st.markdown(f"[🔗 Открыть полную статью на Хабре]({row['url']})")
                st.markdown("---")


# ------------------------------------------
# ВКЛАДКА 2: Аналитика и Тренды (DuckDB)
# ------------------------------------------
with tab_analytics:
    st.subheader("📈 Обзорная статистика базы данных")

    # Верхние карточки метрик
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Всего статей в базе", len(df), help="Количество проанализированных статей в Turso")
    
    top_t = tech_stats.iloc[0]["Технология"] if not tech_stats.empty else "—"
    m2.metric("Топ технология", top_t, help="Самый упоминаемый инструмент")
    
    senior_pct = f"{round((len(df[df['difficulty'] == 'Senior']) / len(df)) * 100)}%" if len(df) > 0 else "0%"
    m3.metric("Доля уровня Senior", senior_pct, help="Процент продвинутых архитектурных статей")

    de_share = len(df[df["hub"] == "Data Engineering"])
    ml_share = len(df[df["hub"] == "Machine Learning"])
    m4.metric("DE / ML баланс", f"{de_share} / {ml_share}", help="Соотношение статей Data Engineering к Machine Learning")

    st.markdown("###")

    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        st.subheader("🔥 Самые востребованные технологии")
        st.caption("Рассчитано движком DuckDB на основе извлеченных сущностей (NER):")
        if not tech_stats.empty:
            st.bar_chart(tech_stats.set_index("Технология"), color="#ff4b4b", height=380)
        else:
            st.info("Данные по стеку будут пополняться по мере выхода новых публикаций.")

    with col_chart2:
        st.subheader("🎯 Распределение по сложности")
        st.caption("Оценка технической глубины моделью Qwen:")
        if not diff_stats.empty:
            st.bar_chart(diff_stats.set_index("Уровень"), color="#1f77b4", height=380)
        else:
            st.info("Статистика уровней сложности формируется.")


# ------------------------------------------
# ВКЛАДКА 3: Экспорт в Data Lake
# ------------------------------------------
with tab_export:
    st.subheader("📦 Экспорт данных в аналитический формат Parquet")
    st.markdown("""
    В современной инженерии данных формат **Apache Parquet** является золотым стандартом для аналитических хранилищ и Data Lake благодаря:
    * **Колоночному хранению** (сжатие в 5–8 раз сильнее CSV/JSON).
    * **Сверхбыстрому чтению** необходимых колонок без сканирования всей таблицы.
    """)

    st.info(f"Текущий размер датасета в Turso: **{len(df)} записей**.")

    if not df.empty:
        parquet_buffer = io.BytesIO()
        export_df = df.drop(columns=["tech_list"])
        export_df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
        parquet_buffer.seek(0)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                label="📥 Скачать датасет (habr_articles.parquet)",
                data=parquet_buffer,
                file_name="habr_articles.parquet",
                mime="application/octet-stream",
                use_container_width=True
            )
        with c2:
            csv_data = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📄 Скачать датасет (habr_articles.csv)",
                data=csv_data,
                file_name="habr_articles.csv",
                mime="text/csv",
                use_container_width=True
            )
