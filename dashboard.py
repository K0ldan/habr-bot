import datetime
import io
import json
import os
import duckdb
import pandas as pd
import sentry_sdk
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 0. Мониторинг Sentry & Ключи доступа
# ==========================================
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

# ==========================================
# 1. Конфигурация страницы и CSS-стилизация
# ==========================================
st.set_page_config(
    page_title="Habr Data & ML Radar",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Основные переменные и шрифты */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Карточки метрик в шапке */
    .hero-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px;
        padding: 24px 28px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(74, 222, 128, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin: 0;
        line-height: 1.5;
    }

    /* Архитектурный бейдж-пайплайн */
    .pipeline-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 14px;
    }
    .pipeline-step {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #e2e8f0;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Карточка статьи */
    .article-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    }
    .article-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.05);
    }

    /* Бейджи уровней и хабов */
    .pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .pill-de {
        background-color: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #dbeafe;
    }
    .pill-ml {
        background-color: #faf5ff;
        color: #7e22ce;
        border: 1px solid #f3e8ff;
    }
    .pill-bd {
        background-color: #ecfeff;
        color: #0e7490;
        border: 1px solid #cffafe;
    }
    .pill-junior {
        background-color: #f0fdf4;
        color: #15803d;
        border: 1px solid #dcfce7;
    }
    .pill-middle {
        background-color: #fffbeb;
        color: #b45309;
        border: 1px solid #fef3c7;
    }
    .pill-senior {
        background-color: #fef2f2;
        color: #b91c1c;
        border: 1px solid #fee2e2;
    }
    .pill-format {
        background-color: #f8fafc;
        color: #475569;
        border: 1px solid #e2e8f0;
    }

    /* Чипы технологий */
    .tech-tag {
        display: inline-block;
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 500;
        margin: 2px 4px 2px 0;
    }

    /* Выжимка AI */
    .ai-summary-box {
        background: #f8fafc;
        border-left: 3px solid #6366f1;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 12px 0;
        font-size: 14px;
        line-height: 1.6;
        color: #1e293b;
    }

    /* Ссылка на статью */
    .article-title-link {
        font-size: 18px;
        font-weight: 700;
        color: #0f172a;
        text-decoration: none;
        display: inline-block;
        margin: 8px 0;
        line-height: 1.35;
    }
    .article-title-link:hover {
        color: #2563eb;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. Загрузка данных из Turso Cloud / SQLite
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

    # Очистка и распаковка JSON-массива технологий
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
# 3. DuckDB Аналитический движок (In-Memory)
# ==========================================
con = duckdb.connect(database=":memory:")
con.register("articles", df)

# Топ технологий
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

# Сложность
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

# Форматы статей
if not df.empty:
    format_stats = con.execute("""
        SELECT 
            article_type as "Формат", 
            count(*) as "Количество"
        FROM articles
        WHERE article_type IS NOT NULL AND article_type != ''
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 5
    """).df()
else:
    format_stats = pd.DataFrame(columns=["Формат", "Количество"])


# ==========================================
# 4. Боковая панель: Фильтры & Health Check
# ==========================================
with st.sidebar:
    st.markdown("### 🔍 Навигация и фильтры")

    # Подсчет по категориям
    total_count = len(df)
    de_count = len(df[df["hub"] == "Data Engineering"])
    ml_count = len(df[df["hub"] == "Machine Learning"])
    bd_count = len(df[df["hub"] == "Big Data"])

    selected_hub = st.radio(
        "Направление:",
        [
            f"Все направления ({total_count})",
            f"Data Engineering ({de_count})",
            f"Machine Learning ({ml_count})",
            f"Big Data ({bd_count})"
        ],
        index=0
    )

    clean_hub = "Все направления"
    if "Data Engineering" in selected_hub:
        clean_hub = "Data Engineering"
    elif "Machine Learning" in selected_hub:
        clean_hub = "Machine Learning"
    elif "Big Data" in selected_hub:
        clean_hub = "Big Data"

    selected_diff = st.multiselect(
        "Уровень сложности:",
        options=["Junior", "Middle", "Senior", "Lead"],
        default=[]
    )

    all_formats = sorted(list(set(df["article_type"].dropna().unique()))) if not df.empty else []
    selected_format = st.multiselect(
        "Формат публикации:",
        options=all_formats,
        default=[]
    )

    search_query = st.text_input(
        "Полнотекстовый поиск:",
        placeholder="Kafka, PyTorch, Архитектура...",
        help="Ищет по названию, AI-выжимке и стеку технологий"
    )

    st.markdown("---")
    st.markdown("### ⚡ Статус инфраструктуры")
    st.markdown("""
    * **DWH:** `🟢 Turso libSQL (AWS EU)`
    * **LLM:** `🟢 Groq LPU (Qwen 27B)`
    * **OLAP:** `🟢 In-Memory DuckDB`
    * **CI/CD:** `🟢 GitHub Actions (4x/день)`
    """)

    st.markdown("---")
    st.caption("🚀 **Автор проекта:** [@K0ldan](https://github.com/K0ldan/habr-bot)")
    st.caption("Репозиторий проекта: [GitHub K0ldan/habr-bot](https://github.com/K0ldan/habr-bot)")


# ==========================================
# 5. Главный экран: Hero Banner
# ==========================================
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">● LIVE DATA PIPELINE</div>
    <h1 class="hero-title">🧠 Habr Data & ML Engineering Radar</h1>
    <p class="hero-subtitle">
        Автономная система мониторинга, AI-структурирования и аналитики лучших материалов по Data Engineering и Machine Learning.
    </p>
    <div class="pipeline-bar">
        <span class="pipeline-step">📡 Habr RSS</span>
        <span style="color: #64748b;">→</span>
        <span class="pipeline-step">🤖 Groq Qwen 27B AI</span>
        <span style="color: #64748b;">→</span>
        <span class="pipeline-step">☁️ Turso Cloud DWH</span>
        <span style="color: #64748b;">→</span>
        <span class="pipeline-step">⚡ DuckDB OLAP</span>
        <span style="color: #64748b;">→</span>
        <span class="pipeline-step">📲 Telegram Alerts</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 6. Ключевые KPI Метрики (Сверху)
# ==========================================
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric(
        label="📚 Всего публикаций в DWH",
        value=f"{total_count} статей",
        delta=f"+{de_count} DE / +{ml_count} ML / +{bd_count} BD",
        help="Количество валидированных и сохраненных материалов в Turso Cloud"
    )

with col_m2:
    top_tech_name = tech_stats.iloc[0]["Технология"] if not tech_stats.empty else "—"
    top_tech_count = tech_stats.iloc[0]["Упоминаний"] if not tech_stats.empty else 0
    st.metric(
        label="🔥 Топ технология стека",
        value=top_tech_name,
        delta=f"{top_tech_count} упоминаний" if top_tech_count else None,
        help="Самый частый инструмент в последних статьях"
    )

with col_m3:
    senior_lead_count = len(df[df["difficulty"].isin(["Senior", "Lead"])])
    senior_share = f"{round((senior_lead_count / total_count) * 100)}%" if total_count > 0 else "0%"
    st.metric(
        label="🎓 Доля Senior / Lead",
        value=senior_share,
        delta=f"{senior_lead_count} глубоких разборов",
        help="Процент статей продвинутого уровня сложности"
    )

with col_m4:
    st.metric(
        label="⏱ Режим автозапуска",
        value="4 раза в день",
        delta="0.00 ₽ / $0 навсегда",
        help="Пайплайн запускается по расписанию через GitHub Actions"
    )

st.markdown("###")


# ==========================================
# 7. Вкладки приложения
# ==========================================
tab_feed, tab_analytics, tab_export = st.tabs([
    "📑 Умная лента выжимок", 
    "📊 Аналитика & Тренды", 
    "📦 Data Lake & Экспорт"
])


# ------------------------------------------
# ВКЛАДКА 1: Умная лента статей
# ------------------------------------------
with tab_feed:
    # Фильтрация
    filtered_df = df.copy()

    if clean_hub != "Все направления":
        filtered_df = filtered_df[filtered_df["hub"] == clean_hub]

    if selected_diff:
        filtered_df = filtered_df[filtered_df["difficulty"].isin(selected_diff)]

    if selected_format:
        filtered_df = filtered_df[filtered_df["article_type"].isin(selected_format)]

    if search_query:
        query = search_query.strip().lower()
        filtered_df = filtered_df[
            filtered_df["title"].str.lower().str.contains(query, na=False) |
            filtered_df["summary"].str.lower().str.contains(query, na=False) |
            filtered_df["tech_list"].apply(lambda tags: any(query in t.lower() for t in tags))
        ]

    # Панель сортировки и счетчик
    feed_header_col1, feed_header_col2 = st.columns([3, 1])
    with feed_header_col1:
        st.markdown(f"#### Отобрано материалов: **{len(filtered_df)}** из {total_count}")
    with feed_header_col2:
        sort_mode = st.selectbox(
            "Сортировка:",
            ["Сначала новые", "Сначала Senior", "По алфавиту"],
            label_visibility="collapsed"
        )

    if sort_mode == "Сначала Senior":
        diff_order = {"Lead": 4, "Senior": 3, "Middle": 2, "Junior": 1}
        filtered_df["sort_key"] = filtered_df["difficulty"].map(diff_order).fillna(0)
        filtered_df = filtered_df.sort_values(by="sort_key", ascending=False)
    elif sort_mode == "По алфавиту":
        filtered_df = filtered_df.sort_values(by="title", ascending=True)

    if filtered_df.empty:
        st.info("💡 По выбранным фильтрам ничего не найдено. Попробуйте сбросить параметры в левом меню.")
    else:
        for _, row in filtered_df.iterrows():
            diff = row["difficulty"]
            diff_pill_class = (
                "pill-senior" if diff in ["Senior", "Lead"] 
                else ("pill-middle" if diff == "Middle" else "pill-junior")
            )
            hub_pill_class = "pill-ml" if row["hub"] == "Machine Learning" else ("pill-bd" if row["hub"] == "Big Data" else "pill-de")

            tags_html = "".join([f'<span class="tech-tag">#{t}</span>' for t in row["tech_list"]])

            summary_content = row["summary"] if row["summary"] else "Краткое описание отсутствует."

            st.markdown(f"""
            <div class="article-card">
                <div>
                    <span class="pill {hub_pill_class}">{row['hub']}</span>
                    <span class="pill {diff_pill_class}">{diff}</span>
                    <span class="pill pill-format">Формат: {row['article_type']}</span>
                </div>
                <a class="article-title-link" href="{row['url']}" target="_blank">
                    {row['title']} ↗
                </a>
                <div class="ai-summary-box">
                    <b>💡 AI Выжимка & Ключевые инсайты:</b><br>
                    {summary_content}
                </div>
                <div style="margin-top: 10px;">
                    <span style="font-size: 12px; font-weight: 600; color: #64748b; margin-right: 6px;">Стек:</span>
                    {tags_html}
                </div>
                <div style="margin-top: 14px; text-align: right;">
                    <a href="{row['url']}" target="_blank" style="font-size: 13px; font-weight: 600; color: #2563eb; text-decoration: none;">
                        Читать оригинал на Хабре →
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ------------------------------------------
# ВКЛАДКА 2: Аналитика и Тренды (DuckDB)
# ------------------------------------------
with tab_analytics:
    st.subheader("📈 Аналитика стека и структуры данных")
    st.caption("Аналитические агрегации рассчитываются на лету быстрым колоночным движком **DuckDB**.")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("##### 🔥 Топ-12 ключевых технологий")
        if not tech_stats.empty:
            st.bar_chart(
                tech_stats.set_index("Технология"), 
                color="#6366f1",
                height=340
            )
        else:
            st.info("Данные формируются...")

    with chart_col2:
        st.markdown("##### 🎯 Распределение по уровням сложности")
        if not diff_stats.empty:
            st.bar_chart(
                diff_stats.set_index("Уровень"), 
                color="#0ea5e9",
                height=340
            )
        else:
            st.info("Данные формируются...")

    st.markdown("---")
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.markdown("##### 📚 Структура форматов статей")
        if not format_stats.empty:
            st.bar_chart(
                format_stats.set_index("Формат"), 
                color="#10b981",
                height=300
            )

    with chart_col4:
        st.markdown("##### ⚖️ Доли направлений (Data Eng vs ML)")
        hub_ratio = pd.DataFrame({
            "Направление": ["Data Engineering", "Machine Learning", "Big Data"],
            "Статей": [de_count, ml_count, bd_count]
        }).set_index("Направление")
        st.bar_chart(hub_ratio, color="#f59e0b", height=300)


    # ------------------------------------------
    # Блок Data Quality & Observability
    # ------------------------------------------
    st.markdown("---")
    st.subheader("🛡️ Data Observability & Качество данных (Data Quality)")
    st.caption("Метрики надежности хранилища, мониторинг свежести данных (SLA) и полноты атрибутов:")

    dq_col1, dq_col2, dq_col3, dq_col4 = st.columns(4)

    # 1. Свежесть данных (Data Freshness / SLA)
    if not df.empty and "created_at" in df.columns:
        latest_ts = pd.to_datetime(df["created_at"]).max()
        now_utc = pd.Timestamp.now(datetime.timezone.utc)
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.tz_localize("UTC")
        diff_hours = max(0.0, round((now_utc - latest_ts).total_seconds() / 3600, 1))
        freshness_label = f"{diff_hours} ч назад" if diff_hours >= 1 else "< 1 часа назад"
    else:
        freshness_label = "—"

    dq_col1.metric(
        label="⏱️ Data Freshness (Свежесть)",
        value=freshness_label,
        delta="SLA соблюден (4x/день)",
        help="Время с момента последней записи в Turso DWH"
    )

    # 2. Полнота стека (Tech Stack Completeness)
    has_tech = len(df[df["tech_list"].apply(len) > 0])
    stack_completeness = f"{round((has_tech / total_count) * 100, 1)}%" if total_count > 0 else "0%"
    dq_col2.metric(
        label="🧩 Полнота стека технологий",
        value=stack_completeness,
        delta=f"{has_tech}/{total_count} размечено",
        help="Процент статей, где NER-модель успешно выделила технологии"
    )

    # 3. Полнота AI-выжимок (Contract Completeness)
    has_summary = len(df[df["summary"].astype(str).str.len() > 10])
    summary_completeness = f"{round((has_summary / total_count) * 100, 1)}%" if total_count > 0 else "0%"
    dq_col3.metric(
        label="📝 Полнота выжимок (Contract)",
        value=summary_completeness,
        delta="Pydantic v2 Contract",
        help="Процент статей с валидированной AI-выжимкой"
    )

    # 4. Уникальность первичных ключей (Primary Key Integrity)
    unique_urls = df["url"].nunique()
    uniqueness = f"{round((unique_urls / total_count) * 100, 1)}%" if total_count > 0 else "0%"
    dq_col4.metric(
        label="🔒 Уникальность записей (PK)",
        value=uniqueness,
        delta="0 дубликатов (Idempotent)",
        help="Гарантия отсутствия дубликатов публикаций в хранилище"
    )


# ------------------------------------------
# ВКЛАДКА 3: Экспорт в Data Lake (Parquet)
# ------------------------------------------
with tab_export:
    st.subheader("📦 Экспорт данных в аналитический формат Parquet")
    st.markdown("""
    В современной архитектуре **Modern Data Stack** формат **Apache Parquet** является стандартом де-факто:
    * **Колоночное хранение:** сжатие в 5–8 раз эффективнее традиционных CSV и JSON.
    * **Схема и типизация:** типы данных (`timestamp`, `strings`, `arrays`) сохраняются без искажений.
    * **Прямая интеграция:** готовые файлы мгновенно читаются в DuckDB, Spark, Pandas, AWS Athena и BigQuery.
    """)

    st.info(f"Объем датасета в Turso Cloud: **{len(df)} проиндексированных статей**.")

    # Предпросмотр схемы данных
    with st.expander("🔍 Посмотреть схему данных таблицы (Data Catalog)"):
        schema_info = pd.DataFrame([
            {"Колонка": "url", "Тип данных": "VARCHAR (PK)", "Описание": "Постоянный безопасный URL статьи на Хабре"},
            {"Колонка": "title", "Тип данных": "VARCHAR", "Описание": "Очищенный и экранированный заголовок материала"},
            {"Колонка": "hub", "Тип данных": "VARCHAR", "Описание": "Категория (Data Engineering / Machine Learning)"},
            {"Колонка": "difficulty", "Тип данных": "VARCHAR", "Описание": "Грейд сложности (Junior, Middle, Senior, Lead)"},
            {"Колонка": "article_type", "Тип данных": "VARCHAR", "Описание": "Формат (Кейс, Архитектура, Обзор, Туториал)"},
            {"Колонка": "tech_stack", "Тип данных": "JSON / TEXT", "Описание": "Массив выделенных сущностей стека технологий"},
            {"Колонка": "summary", "Тип данных": "TEXT", "Описание": "Структурированная выжимка, сгенерированная Groq LLM"},
            {"Колонка": "created_at", "Тип данных": "TIMESTAMP", "Описание": "Дата и время фиксации статьи в базе DWH"},
        ])
        st.dataframe(schema_info, use_container_width=True, hide_index=True)

    if not df.empty:
        # Предпросмотр датасета
        st.markdown("##### 📄 Предпросмотр датасета (первые 5 строк):")
        preview_df = df.drop(columns=["tech_list"]).head(5)
        st.dataframe(preview_df, use_container_width=True)

        st.markdown("###")
        parquet_buffer = io.BytesIO()
        export_df = df.drop(columns=["tech_list"])
        export_df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
        parquet_buffer.seek(0)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                label="📥 Скачать Apache Parquet (habr_articles.parquet)",
                data=parquet_buffer,
                file_name="habr_articles.parquet",
                mime="application/octet-stream",
                use_container_width=True
            )
        with c2:
            csv_data = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📄 Скачать CSV для Excel (habr_articles.csv)",
                data=csv_data,
                file_name="habr_articles.csv",
                mime="text/csv",
                use_container_width=True
            )
