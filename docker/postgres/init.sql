-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Тестовая база данных (изолирована от продакшн)
CREATE DATABASE tutor_bot_test OWNER abmine;

-- Создание схемы (опционально)
-- CREATE SCHEMA IF NOT EXISTS tutor;

-- Можно добавить начальные данные
-- INSERT INTO students (name, subject, phone) VALUES 
-- ('Иван Иванов', 'Математика', '+79161234567'),
-- ('Мария Петрова', 'Английский', '+79169876543');