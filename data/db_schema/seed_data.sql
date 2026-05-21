-- OpsAgent 种子数据
USE ops_agent;

-- 服务器 (20台)
INSERT INTO servers (hostname, ip, os, cpu_cores, memory_gb, disk_gb, location, status) VALUES
('web-01', '192.168.1.10', 'CentOS 7', 8, 32, 500, '北京机房', 'online'),
('web-02', '192.168.1.11', 'CentOS 7', 8, 32, 500, '北京机房', 'online'),
('web-03', '192.168.1.12', 'Ubuntu 20.04', 16, 64, 1000, '北京机房', 'online'),
('db-master', '192.168.1.20', 'CentOS 7', 16, 64, 2000, '北京机房', 'online'),
('db-slave-1', '192.168.1.21', 'CentOS 7', 16, 64, 2000, '北京机房', 'online'),
('db-slave-2', '192.168.1.22', 'CentOS 7', 16, 64, 2000, '上海机房', 'online'),
('cache-01', '192.168.1.30', 'CentOS 7', 4, 16, 200, '北京机房', 'online'),
('cache-02', '192.168.1.31', 'CentOS 7', 4, 16, 200, '北京机房', 'online'),
('mq-01', '192.168.1.40', 'CentOS 7', 8, 32, 500, '北京机房', 'online'),
('mq-02', '192.168.1.41', 'CentOS 7', 8, 32, 500, '上海机房', 'maintenance'),
('monitor-01', '192.168.1.50', 'Ubuntu 20.04', 4, 16, 500, '北京机房', 'online'),
('log-01', '192.168.1.60', 'Ubuntu 20.04', 8, 32, 2000, '北京机房', 'online'),
('app-01', '192.168.1.70', 'CentOS 7', 16, 64, 1000, '北京机房', 'online'),
('app-02', '192.168.1.71', 'CentOS 7', 16, 64, 1000, '北京机房', 'online'),
('app-03', '192.168.1.72', 'CentOS 7', 16, 64, 1000, '上海机房', 'online'),
('app-04', '192.168.1.73', 'CentOS 7', 16, 64, 1000, '上海机房', 'offline'),
('dns-01', '192.168.1.80', 'CentOS 7', 2, 8, 100, '北京机房', 'online'),
('lb-01', '192.168.1.90', 'CentOS 7', 4, 16, 200, '北京机房', 'online'),
('lb-02', '192.168.1.91', 'CentOS 7', 4, 16, 200, '上海机房', 'online'),
('dev-01', '192.168.2.10', 'Ubuntu 20.04', 8, 32, 500, '北京机房', 'online');

-- 服务 (50个)
INSERT INTO services (server_id, service_name, port, version, status, last_restart) VALUES
(1, 'nginx', 80, '1.24.0', 'running', '2026-05-15 08:00:00'),
(1, 'nginx', 443, '1.24.0', 'running', '2026-05-15 08:00:00'),
(2, 'nginx', 80, '1.24.0', 'running', '2026-05-15 08:00:00'),
(3, 'nginx', 80, '1.24.0', 'running', '2026-05-14 12:00:00'),
(4, 'mysql', 3306, '8.0.35', 'running', '2026-05-10 02:00:00'),
(5, 'mysql', 3306, '8.0.35', 'running', '2026-05-10 02:00:00'),
(6, 'mysql', 3306, '8.0.35', 'running', '2026-05-10 02:00:00'),
(7, 'redis', 6379, '7.2.0', 'running', '2026-05-14 06:00:00'),
(8, 'redis', 6379, '7.2.0', 'running', '2026-05-14 06:00:00'),
(9, 'rabbitmq', 5672, '3.12.0', 'running', '2026-05-13 00:00:00'),
(10, 'rabbitmq', 5672, '3.12.0', 'stopped', NULL),
(11, 'prometheus', 9090, '2.45.0', 'running', '2026-05-12 00:00:00'),
(11, 'grafana', 3000, '10.0.0', 'running', '2026-05-12 00:00:00'),
(11, 'alertmanager', 9093, '0.25.0', 'running', '2026-05-12 00:00:00'),
(12, 'elasticsearch', 9200, '8.11.0', 'running', '2026-05-11 00:00:00'),
(12, 'logstash', 5044, '8.11.0', 'running', '2026-05-11 00:00:00'),
(12, 'kibana', 5601, '8.11.0', 'running', '2026-05-11 00:00:00'),
(13, 'tomcat', 8080, '9.0.80', 'running', '2026-05-15 06:00:00'),
(14, 'tomcat', 8080, '9.0.80', 'running', '2026-05-15 06:00:00'),
(15, 'tomcat', 8080, '9.0.80', 'running', '2026-05-15 06:00:00'),
(16, 'tomcat', 8080, '9.0.80', 'degraded', NULL),
(17, 'bind9', 53, '9.18.0', 'running', '2026-04-01 00:00:00'),
(18, 'haproxy', 80, '2.8.0', 'running', '2026-05-01 00:00:00'),
(19, 'haproxy', 80, '2.8.0', 'running', '2026-05-01 00:00:00');

INSERT INTO services (server_id, service_name, port, version, status, last_restart) VALUES
(4, 'mysqld_exporter', 9104, '0.15.0', 'running', '2026-05-10 02:00:00'),
(5, 'mysqld_exporter', 9104, '0.15.0', 'running', '2026-05-10 02:00:00'),
(7, 'redis_exporter', 9121, '1.58.0', 'running', '2026-05-14 06:00:00'),
(8, 'redis_exporter', 9121, '1.58.0', 'running', '2026-05-14 06:00:00'),
(11, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(1, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(2, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(3, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(4, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(5, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(13, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(14, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(15, 'node_exporter', 9100, '1.6.0', 'running', '2026-05-12 00:00:00'),
(20, 'jenkins', 8080, '2.440.0', 'running', '2026-05-08 00:00:00'),
(20, 'gitlab', 8443, '16.8.0', 'running', '2026-05-08 00:00:00'),
(13, 'java_app', 8081, '1.5.0', 'running', '2026-05-15 06:00:00'),
(14, 'java_app', 8081, '1.5.0', 'running', '2026-05-15 06:00:00'),
(15, 'java_app', 8081, '1.5.0', 'running', '2026-05-15 06:00:00'),
(16, 'java_app', 8082, '1.4.0', 'stopped', NULL),
(4, 'keepalived', 0, '2.2.0', 'running', '2026-05-01 00:00:00'),
(18, 'keepalived', 0, '2.2.0', 'running', '2026-05-01 00:00:00'),
(19, 'keepalived', 0, '2.2.0', 'running', '2026-05-01 00:00:00');

-- 用户 (30人)
INSERT INTO users (username, real_name, department, role, email) VALUES
('zhangsan', '张三', '基础运维部', 'admin', 'zhangsan@company.com'),
('lisi', '李四', '基础运维部', 'operator', 'lisi@company.com'),
('wangwu', '王五', '基础运维部', 'operator', 'wangwu@company.com'),
('zhaoliu', '赵六', '基础运维部', 'viewer', 'zhaoliu@company.com'),
('sunqi', '孙七', '基础运维部', 'operator', 'sunqi@company.com'),
('zhouba', '周八', 'DBA团队', 'admin', 'zhouba@company.com'),
('wujiu', '吴九', 'DBA团队', 'operator', 'wujiu@company.com'),
('zhengshi', '郑十', 'DBA团队', 'operator', 'zhengshi@company.com'),
('qianyi', '钱一', 'DBA团队', 'viewer', 'qianyi@company.com'),
('liuer', '刘二', '网络运维部', 'admin', 'liuer@company.com'),
('chensan', '陈三', '网络运维部', 'operator', 'chensan@company.com'),
('yangsi', '杨四', '网络运维部', 'operator', 'yangsan@company.com'),
('huangwu', '黄五', '网络运维部', 'viewer', 'huangwu@company.com'),
('xuliu', '徐六', '安全部', 'admin', 'xuliu@company.com'),
('maqi', '马七', '安全部', 'operator', 'maqi@company.com'),
('linba', '林八', '安全部', 'viewer', 'linba@company.com');

INSERT INTO users (username, real_name, department, role, email) VALUES
('hejiu', '何九', '基础运维部', 'operator', 'hejiu@company.com'),
('gaoshi', '高十', '基础运维部', 'operator', 'gaoshi@company.com'),
('luoyi', '罗一', 'DBA团队', 'operator', 'luoyi@company.com'),
('lianger', '梁二', '网络运维部', 'operator', 'lianger@company.com'),
('songsi', '宋四', '安全部', 'operator', 'songsi@company.com'),
('tangwu', '唐五', '基础运维部', 'viewer', 'tangwu@company.com'),
('hanliu', '韩六', 'DBA团队', 'viewer', 'hanliu@company.com'),
('fengqi', '冯七', '网络运维部', 'viewer', 'fengqi@company.com'),
('caoba', '曹八', '安全部', 'viewer', 'caoba@company.com'),
('dengjiu', '邓九', '基础运维部', 'operator', 'dengjiu@company.com'),
('xushi', '许十', '基础运维部', 'operator', 'xushi@company.com'),
('shenyi', '沈一', 'DBA团队', 'operator', 'shenyi@company.com'),
('weier', '魏二', '网络运维部', 'operator', 'weier@company.com'),
('jiangsi', '姜四', '安全部', 'operator', 'jiangsi@company.com');

-- 告警 (200条，过去30天)
INSERT INTO alerts (server_id, severity, title, message, created_at, resolved_at, status) VALUES
(4, 'critical', '数据库主库磁盘使用率超过90%', 'db-master /dev/sda1 磁盘使用率达到94%，需立即扩容', '2026-05-15 08:00:00', '2026-05-15 09:30:00', 'resolved'),
(4, 'warning', 'MySQL连接数接近上限', '当前连接数420/500，建议检查连接池配置', '2026-05-15 10:00:00', NULL, 'open'),
(1, 'critical', 'CPU使用率持续100%超过10分钟', 'web-01 CPU使用率100%，top显示java进程占用过高', '2026-05-15 11:00:00', NULL, 'open'),
(3, 'warning', '内存使用率超过85%', 'web-03 内存使用率87%，可能影响服务性能', '2026-05-15 09:00:00', '2026-05-15 12:00:00', 'resolved'),
(16, 'critical', 'app-04 服务down', 'app-04 上所有tomcat实例停止响应', '2026-05-15 02:00:00', NULL, 'acknowledged'),
(10, 'warning', 'mq-02 RabbitMQ未运行', 'mq-02 RabbitMQ服务状态为stopped', '2026-05-14 12:00:00', NULL, 'open'),
(3, 'critical', '磁盘IO等待时间过长', 'web-03 iowait达到30%，磁盘可能存在故障', '2026-05-14 08:00:00', '2026-05-14 15:00:00', 'resolved'),
(1, 'info', 'nginx访问日志增长过快', 'web-01 nginx日志昨日增量50GB', '2026-05-14 06:00:00', '2026-05-14 10:00:00', 'resolved'),
(5, 'warning', '主从复制延迟超过60秒', 'db-slave-1 与 db-master 复制延迟达到65s', '2026-05-14 07:30:00', NULL, 'open'),
(2, 'critical', 'SSL证书即将过期', 'web-02 SSL证书将在7天后过期', '2026-05-13 09:00:00', NULL, 'open'),
(12, 'warning', 'Elasticsearch集群状态yellow', 'log-01 ES集群状态变为yellow，部分副本未分配', '2026-05-13 11:00:00', '2026-05-13 14:00:00', 'resolved'),
(18, 'critical', 'LB主节点健康检查失败', 'lb-01 后端服务健康检查连续3次失败', '2026-05-13 15:00:00', '2026-05-13 16:00:00', 'resolved'),
(7, 'warning', 'Redis内存使用率达到80%', 'cache-01 Redis内存使用80%，建议扩容', '2026-05-13 10:00:00', NULL, 'acknowledged'),
(9, 'info', 'RabbitMQ消息堆积', 'mq-01 消息堆积超过10000条', '2026-05-12 14:00:00', '2026-05-12 15:00:00', 'resolved'),
(20, 'warning', 'Jenkins构建队列积压', 'dev-01 Jenkins构建队列积压12个任务', '2026-05-12 08:00:00', '2026-05-12 10:00:00', 'resolved');

-- 更多告警 (简化，批量插入)
INSERT INTO alerts (server_id, severity, title, message, created_at, resolved_at, status)
SELECT
    (server_id % 20) + 1,
    ELT((FLOOR(RAND() * 3) + 1), 'critical', 'warning', 'info'),
    CONCAT('告警-', n, ': ', ELT((FLOOR(RAND() * 4) + 1),
        'CPU使用率异常', '内存不足', '磁盘空间不足', '服务响应超时')),
    CONCAT('自动生成的告警消息 #', n),
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY),
    IF(RAND() > 0.5, DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 5) DAY), NULL),
    ELT((FLOOR(RAND() * 3) + 1), 'open', 'acknowledged', 'resolved')
FROM
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) a,
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) b,
    (SELECT 1 AS n UNION SELECT 2) c
WHERE a.n * b.n * c.n <= 185;

-- 工单 (100条)
INSERT INTO tickets (user_id, server_id, title, description, priority, status, created_at, resolved_at) VALUES
(1, 4, '数据库主库磁盘扩容', 'db-master磁盘使用率超90%，需紧急扩容至3TB', 'high', 'resolved', '2026-05-15 08:10:00', '2026-05-15 10:00:00'),
(2, 1, 'web-01 CPU使用率过高排查', '用户反馈web-01服务响应缓慢，需排查CPU使用率过高原因', 'high', 'in_progress', '2026-05-15 11:10:00', NULL),
(3, 3, 'web-03 内存升级', 'web-03 内存不足，需从64GB升级至128GB', 'medium', 'open', '2026-05-15 09:20:00', NULL),
(4, 16, 'app-04 服务恢复', 'app-04上所有tomcat实例停止，需紧急恢复', 'high', 'in_progress', '2026-05-15 02:30:00', NULL),
(6, 5, '主从复制延迟修复', 'db-slave-1与db-master复制延迟超60s，需排查复制通道', 'high', 'open', '2026-05-14 07:40:00', NULL),
(10, 2, 'SSL证书更新', 'web-02 SSL证书7天后过期，需更新证书', 'high', 'open', '2026-05-13 09:10:00', NULL),
(1, 10, 'mq-02 RabbitMQ服务启动', 'mq-02 RabbitMQ服务状态异常，需重启并排查原因', 'medium', 'open', '2026-05-14 12:10:00', NULL),
(7, 7, 'Redis扩容评估', 'cache-01 Redis内存使用率80%，需评估扩容方案', 'medium', 'open', '2026-05-13 10:10:00', NULL),
(8, 18, 'LB健康检查配置优化', 'lb-01后端健康检查阈值需调整', 'low', 'resolved', '2026-05-13 15:10:00', '2026-05-13 17:00:00'),
(11, 12, 'ES集群yellow状态处理', 'log-01 ES集群yellow，需分配副本', 'medium', 'resolved', '2026-05-13 11:10:00', '2026-05-13 14:00:00');

-- 更多工单
INSERT INTO tickets (user_id, server_id, title, description, priority, status, created_at, resolved_at)
SELECT
    (FLOOR(RAND() * 30) + 1),
    (FLOOR(RAND() * 20) + 1),
    CONCAT('工单-', n, ': ', ELT((FLOOR(RAND() * 5) + 1),
        '服务器例行巡检', '服务性能优化', '安全补丁更新', '日志归档处理', '监控告警处理')),
    CONCAT('描述内容 #', n),
    ELT((FLOOR(RAND() * 3) + 1), 'high', 'medium', 'low'),
    ELT((FLOOR(RAND() * 4) + 1), 'open', 'in_progress', 'resolved', 'closed'),
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY),
    IF(RAND() > 0.5, DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 10) DAY), NULL)
FROM
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) a,
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b
WHERE a.n * b.n <= 90;

-- 性能指标 (1000条，7天 x 24小时 x 6台服务器约=1008条)
INSERT INTO performance_metrics (server_id, cpu_usage, memory_usage, disk_usage, collected_at)
SELECT
    (FLOOR(RAND() * 6) + 1) AS server_id,
    ROUND(20 + RAND() * 60, 2) AS cpu_usage,
    ROUND(30 + RAND() * 50, 2) AS memory_usage,
    ROUND(40 + RAND() * 50, 2) AS disk_usage,
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 168) HOUR) AS collected_at
FROM
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) a,
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) b,
    (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) c;
