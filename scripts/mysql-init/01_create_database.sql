-- Idempotent database + privilege setup run once on first container start.
-- Alembic manages the schema from this point forward.

CREATE DATABASE IF NOT EXISTS `pronunciation_coach`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Grant full privileges to the application user (already created via env vars)
GRANT ALL PRIVILEGES ON `pronunciation_coach`.* TO 'pronunciation'@'%';
FLUSH PRIVILEGES;
