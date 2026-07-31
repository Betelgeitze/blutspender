# Graph Report - .  (2026-07-30)

## Corpus Check
- Corpus is ~4,918 words - fits in a single context window. You may not need a graph.

## Summary
- 97 nodes · 170 edges · 7 communities (4 shown, 3 thin omitted)
- Extraction: 90% EXTRACTED · 9% INFERRED · 1% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.86)
- Token cost: 45,816 input · 0 output

## Community Hubs (Navigation)
- Database Access Layer
- Service Dependencies and Config
- Parsing and Date Utilities
- Telegram Bot Interface
- AWS Deployment and Scheduling
- Notification Formatting and Sending

## God Nodes (most connected - your core abstractions)
1. `ManageDB` - 30 edges
2. `DateManager` - 13 edges
3. `msg()` - 12 edges
4. `PostcodeRanges` - 9 edges
5. `Bot Dependency Set` - 7 edges
6. `send_postcode()` - 5 edges
7. `Blood Donation Appointment Parsing (DRK website)` - 5 edges
8. `PostgreSQL Appointment Database` - 5 edges
9. `welcome_message()` - 4 edges
10. `handle_callback_query()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `APScheduler 3.9.1 (in-process scheduling)` --semantically_similar_to--> `AWS EventBridge Daily Scheduling`  [INFERRED] [semantically similar]
  bot/requirements.txt → README.md
- `Sender Dependency Set` --semantically_similar_to--> `Bot Dependency Set`  [INFERRED] [semantically similar]
  sender/requirements.txt → bot/requirements.txt
- `psycopg2-binary driver choice (bot)` --semantically_similar_to--> `psycopg2 source driver (parser)`  [INFERRED] [semantically similar]
  bot/requirements.txt → parser/requirements.txt
- `beautifulsoup4 + lxml HTML scraping stack` --implements--> `Blood Donation Appointment Parsing (DRK website)`  [INFERRED]
  parser/requirements.txt → README.md
- `SQLAlchemy 2.0.0 ORM layer (bot)` --implements--> `PostgreSQL Appointment Database`  [INFERRED]
  bot/requirements.txt → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Three-Service Architecture (bot, parser, sender) over one Postgres DB** — docker_compose_bot_service, docker_compose_parser_service, docker_compose_sender_service, docker_compose_database_service [EXTRACTED 1.00]
- **Appointment Notification Pipeline** — readme_blood_donation_appointment_parsing, readme_postgres_database, readme_postcode_distance_matching, readme_reminder_sender_flow, readme_telegram_bot_api [EXTRACTED 1.00]
- **Shared Core Dependency Stack (SQLAlchemy, pgeocode, requests, psycopg2)** — bot_requirements_dependency_set, parser_requirements_dependency_set, sender_requirements_dependency_set [INFERRED 0.95]

## Communities (7 total, 3 thin omitted)

### Community 1 - "Service Dependencies and Config"
Cohesion: 0.14
Nodes (21): Bot Dependency Set, pgeocode geocoding library (bot), psycopg2-binary driver choice (bot), pyTelegramBotAPI 4.9.0 (bot), SQLAlchemy 2.0.0 ORM layer (bot), docker-compose bot service, docker-compose database service (postgres:latest), docker-compose parser service (commented out) (+13 more)

### Community 3 - "Telegram Bot Interface"
Cohesion: 0.22
Nodes (16): change_language(), create_donation_confirmed_keyboard(), create_language_keyboard(), create_main_keyboard(), create_manage_postcodes_keyboard(), create_settings_keyboard(), create_stop_reminder_length_keyboard(), create_stop_reminder_reason_keyboard() (+8 more)

### Community 4 - "AWS Deployment and Scheduling"
Cohesion: 0.22
Nodes (9): APScheduler 3.9.1 (in-process scheduling), Shared .env File Across Services, AWS EventBridge Daily Scheduling, AWS Lambda Deployment (ECR image), BlutspenderBot, Container Deployment on AWS ECS, Environment Credential Variables (BOT_API_KEY, POSTGRES_*), Telegram Bot API / BotFather Registration (+1 more)

## Ambiguous Edges - Review These
- `Telegram Bot API / BotFather Registration` → `AWS Lambda Deployment (ECR image)`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **2 isolated node(s):** `Telegram Update Payload Example (/menu command)`, `pyTelegramBotAPI 4.9.0 (bot)`
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Telegram Bot API / BotFather Registration` and `AWS Lambda Deployment (ECR image)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `ManageDB` connect `Database Access Layer` to `Parsing and Date Utilities`, `Telegram Bot Interface`, `Notification Formatting and Sending`?**
  _High betweenness centrality (0.261) - this node is a cross-community bridge._
- **Why does `DateManager` connect `Parsing and Date Utilities` to `Database Access Layer`, `Telegram Bot Interface`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `PostcodeRanges` connect `Parsing and Date Utilities` to `Database Access Layer`, `Telegram Bot Interface`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ManageDB` (e.g. with `DateManager` and `PostcodeRanges`) actually correct?**
  _`ManageDB` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Bot Dependency Set` (e.g. with `docker-compose bot service` and `Sender Dependency Set`) actually correct?**
  _`Bot Dependency Set` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Telegram Update Payload Example (/menu command)`, `pyTelegramBotAPI 4.9.0 (bot)` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._