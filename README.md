# 🧠 Habr Data & ML Intelligence Platform (with DevSecOps)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Security: Bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Автоматизированная платформа и serverless ELT-пайплайн для мониторинга, семантического анализа и агрегации технических публикаций с Хабра по направлениям **Data Engineering** и **Machine Learning**.

Проект разработан с соблюдением принципов разделения вычислений и хранилища (**Separation of Compute and Storage**) и встроенным контуром безопасности (**DevSecOps**) с нулевой стоимостью инфраструктуры ($0 Cloud Architecture).

---

## 🏗 Архитектура системы

```mermaid
flowchart TD
    subgraph Ingestion ["Сбор данных и AI-Кураторство"]
        A["Habr RSS Feeds (DE & ML)"] --> B["GitHub Actions Runner"]
        B --> C["Groq API (Qwen 27B)"]
    end

    subgraph Security ["DevSecOps Security Gate"]
        B --> S1["Bandit (SAST Security Scan)"]
        B --> S2["pip-audit (CVE Vulnerability Audit)"]
        C --> S3["Prompt Injection Defense"]
    end

    subgraph Storage ["Хранилище и Контракты"]
        C --> D["Pydantic Data Contracts"]
        D -->|OLTP| E["Turso Cloud Database (libSQL / SQLite)"]
    end

    subgraph Serving ["Доставка и Аналитика"]
        D -->|Bot Delivery| F["Telegram Bot (Дайджест с хэштегами)"]
        E -->|OLAP Engine| G["DuckDB (In-Memory Processing)"]
        G --> H["Streamlit Web Dashboard"]
        G --> I["Apache Parquet Export"]
    end
```

---

## 🛡 Контур безопасности (DevSecOps)

В проекте реализован 4-уровневый контур безопасности без использования платных инструментов:
1. **AppSec:**
   * **Prompt Injection Defense:** фильтрация мета-команд в текстах статей.
   * **SQL Injection Prevention:** 100% параметризованные SQL-запросы в Turso и DuckDB.
   * **XSS / HTML Sanitization:** экранирование спецсимволов перед отправкой в Telegram API.
2. **SAST (Static Application Security Testing):**
   * Анализ исходного кода через **Bandit** на уязвимости, небезопасные вызовы и утечки.
3. **SCA (Software Composition Analysis):**
   * Аудит зависимостей через **pip-audit** по мировой базе уязвимостей CVE.
4. **Least Privilege (Принцип наименьших привилегий):**
   * Виртуальные машины GitHub Actions работают с правами `contents: read` без доступа к изменению репозитория.

---

## 🛠 Технологический стек

* **Оркестрация:** GitHub Actions (расписание: 09:00, 13:00, 18:00, 22:00 МСК).
* **AI & NER:** **Groq Cloud API** (`qwen/qwen3.8-27b`) — фильтрация шума, извлечение стека технологий и уровня сложности.
* **Качество данных (Data Quality):** **Pydantic v2** — валидация контрактов данных.
* **Облачное хранилище (DWH):** **Turso** (Serverless libSQL) в защищённом регионе Стокгольм.
* **Аналитический движок (OLAP):** **DuckDB** — векторные вычисления и агрегация тегов через функцию `unnest()`.
* **Визуализация (BI):** **Streamlit** — реактивный веб-дашборд с фильтрами по стеку.
* **Формат данных:** **Apache Parquet** (`pyarrow`) — генерация аналитического файла на лету.

---

## 🚀 Быстрый старт

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/habr-bot.git
   cd habr-bot
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Запуск пайплайна:
   ```bash
   python main.py
   ```

4. Запуск аналитического дашборда:
   ```bash
   streamlit run dashboard.py
   ```
