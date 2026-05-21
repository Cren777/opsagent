-- OpsAgent 模拟企业IT运维数据库
-- MySQL 8.0+

CREATE DATABASE IF NOT EXISTS ops_agent DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ops_agent;

-- 1. 服务器表
CREATE TABLE IF NOT EXISTS servers (
    server_id INT AUTO_INCREMENT PRIMARY KEY,
    hostname VARCHAR(64) NOT NULL UNIQUE,
    ip VARCHAR(45) NOT NULL,
    os VARCHAR(32) NOT NULL DEFAULT 'CentOS 7',
    cpu_cores INT NOT NULL DEFAULT 8,
    memory_gb INT NOT NULL DEFAULT 32,
    disk_gb INT NOT NULL DEFAULT 500,
    location VARCHAR(32) NOT NULL DEFAULT '北京机房',
    status ENUM('online','offline','maintenance') NOT NULL DEFAULT 'online',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. 服务表
CREATE TABLE IF NOT EXISTS services (
    service_id INT AUTO_INCREMENT PRIMARY KEY,
    server_id INT NOT NULL,
    service_name VARCHAR(64) NOT NULL,
    port INT NOT NULL,
    version VARCHAR(16) DEFAULT '',
    status ENUM('running','stopped','degraded') NOT NULL DEFAULT 'running',
    last_restart TIMESTAMP NULL,
    FOREIGN KEY (server_id) REFERENCES servers(server_id)
) ENGINE=InnoDB;

-- 3. 告警表
CREATE TABLE IF NOT EXISTS alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    server_id INT NOT NULL,
    severity ENUM('critical','warning','info') NOT NULL,
    title VARCHAR(128) NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    status ENUM('open','acknowledged','resolved') NOT NULL DEFAULT 'open',
    FOREIGN KEY (server_id) REFERENCES servers(server_id)
) ENGINE=InnoDB;

-- 4. 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(32) NOT NULL UNIQUE,
    real_name VARCHAR(32) NOT NULL,
    department VARCHAR(32) NOT NULL,
    role ENUM('admin','operator','viewer') NOT NULL DEFAULT 'operator',
    email VARCHAR(64)
) ENGINE=InnoDB;

-- 5. 工单表
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    server_id INT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority ENUM('high','medium','low') NOT NULL DEFAULT 'medium',
    status ENUM('open','in_progress','resolved','closed') NOT NULL DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (server_id) REFERENCES servers(server_id)
) ENGINE=InnoDB;

-- 6. 性能指标表
CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_id INT AUTO_INCREMENT PRIMARY KEY,
    server_id INT NOT NULL,
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers(server_id)
) ENGINE=InnoDB;
