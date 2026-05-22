# Сервис управления данными — быстрый запуск

## Требования
- Docker, Docker Compose
- 8 ГБ ОЗУ

## 1. Подготовка окружения

Скопируйте `.env.example` в `.env` (если есть) или отредактируйте переменные в `docker-compose.yml`:
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mvp_db
DATABASE_URL=postgresql://postgres:postgres@db:5432/mvp_db
AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:postgres@db:5432/airflow_db
AIRFLOW_CONN_POSTGRES_DEFAULT=postgresql://postgres:postgres@db:5432/mvp_db

## 2. Создание баз данных и таблиц

# Создать базу метаданных Airflow
docker-compose up -d db
docker exec -it $(docker ps -qf "name=db") psql -U postgres -c "CREATE DATABASE airflow_db;"

# Создать таблицы (staging, финальные, логи)
docker exec -i $(docker ps -qf "name=db") psql -U postgres -d mvp_db < create_staging.sql

# Инициализировать Airflow (только при первом запуске)
docker-compose run --rm etl airflow db init
docker-compose run --rm etl airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com

## 3. Запуск всех сервисов
docker-compose up -d --build

## 4. Доступ к сервисам

| Компонент               | URL                                          |
|------------------------|----------------------------------------------|
| Web-интерфейс + API    | `http://localhost:8000`                      |
| Swagger документация   | `http://localhost:8000/docs`                 |
| Airflow UI             | `http://localhost:8081` (логин/пароль: admin/admin) |
| PostgreSQL             | `localhost:5432` (базы данных: `mvp_db`, `airflow_db`) |

## 5. Остановка
docker-compose down
Данные сохраняются (тома postgres_data, shared_data).

Файлы для редактирования (при кастомизации)
docker-compose.yml – порты, переменные окружения, монтирования.

.env – чувствительные данные (пароли, ключи).

create_staging.sql – схема БД (при изменении структуры).

## 6. Логи
docker-compose logs -f app       # FastAPI
docker-compose logs -f etl       # Airflow + Spark
docker-compose logs -f db        # PostgreSQL