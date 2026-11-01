-- ============================================
-- LLM Collection Database Init Script
-- ============================================

CREATE DATABASE IF NOT EXISTS `ai_service` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS `chat_history` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE `ai_service`;

-- User table
DROP TABLE IF EXISTS `ai_user`;
CREATE TABLE `ai_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uuid` varchar(50) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `realname` varchar(50) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `additional_info` json,
  `platform_sort` json,
  `preferences` json,
  `create_time` datetime DEFAULT NULL,
  `create_by` varchar(50) DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `update_by` varchar(50) DEFAULT NULL,
  `is_del` int NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_uuid` (`uuid`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_realname` (`realname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Physical node table
DROP TABLE IF EXISTS `ai_physical_node`;
CREATE TABLE `ai_physical_node` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uuid` varchar(50) NOT NULL,
  `name` varchar(100) NOT NULL,
  `node_ip` varchar(100) NOT NULL,
  `username` varchar(100) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `port` int DEFAULT 22,
  `timeout` int DEFAULT 60,
  `additional_info` json DEFAULT NULL,
  `create_time` datetime NOT NULL,
  `create_by` varchar(50) NOT NULL,
  `update_time` datetime NOT NULL,
  `update_by` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_uuid` (`uuid`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Default admin user (password: 123456, use werkzeug generate_password_hash in production)
INSERT INTO `ai_user` (`uuid`, `username`, `realname`, `password`, `additional_info`, `platform_sort`, `preferences`, `create_time`, `create_by`, `update_time`, `update_by`, `is_del`)
VALUES ('admin-uuid-001', 'admin', 'admin', 'scrypt:32768:8:1$peQmLAQPx4DmQRwX$dca7d5744d9e53a40bc017af08493bea2db4c6c3ff9a3c45f15d650cb1ffb084378dacd8a6bf11024312d3f14b08bbc764a4d8a492a41483cd17d676dfd9fe2e', '{}', '{}', '{}', NOW(), 'system', NOW(), 'system', 0)
ON DUPLICATE KEY UPDATE `update_time` = NOW();
