# MySQL 常见故障处理

## 数据库无法启动

### 排查步骤
1. 查看错误日志：
```bash
tail -100 /var/log/mysql/error.log
```

2. 常见原因：
- **磁盘空间满**：`df -h` 检查
- **配置文件错误**：`mysqld --validate-config`
- **端口被占用**：`ss -tlnp | grep 3306`
- **数据文件损坏**：需要InnoDB恢复
- **内存不足**：innodb_buffer_pool_size 设置过大

3. InnoDB恢复模式：
```ini
# my.cnf
[mysqld]
innodb_force_recovery = 1   # 从1开始尝试
# 1: 跳过损坏页
# 2: 不启动后台线程
# 3: 不进行事务回滚
# 4: 不加载INSERT BUFFER
# 5: 不查看undo log
# 6: 不进行前滚
```

## 表损坏修复

```sql
-- 检查表
CHECK TABLE table_name;

-- 修复表（MyISAM）
REPAIR TABLE table_name;

-- InnoDB 表修复
ALTER TABLE table_name ENGINE=InnoDB;
```

## OOM（Out of Memory）问题

### 预防措施
```ini
# my.cnf
innodb_buffer_pool_size = 60%_of_RAM  # 不要设太大
max_connections = 500                 # 限制连接数
performance_schema = OFF              # 节省内存（生产环境慎用）
```

### 发生OOM后
1. 检查系统日志：`dmesg | grep -i "killed process"`
2. 检查MySQL错误日志
3. 降低buffer_pool_size后重启
4. 考虑添加更多物理内存或配置swap

## 连接数满

```sql
-- 紧急处理：kill掉长时间Sleep的连接
SELECT CONCAT('KILL ', id, ';') 
FROM information_schema.PROCESSLIST 
WHERE COMMAND = 'Sleep' AND TIME > 300;

-- 或批量kill
SELECT GROUP_CONCAT(id) INTO @ids
FROM information_schema.PROCESSLIST WHERE TIME > 600;
-- 然后手动执行 KILL @id

-- 修改最大连接数
SET GLOBAL max_connections = 1000;
-- 持久化到 my.cnf
```

## 表锁等待

```sql
-- 查看InnoDB锁等待
SELECT
  r.trx_id waiting_trx_id,
  r.trx_mysql_thread_id waiting_thread,
  r.trx_query waiting_query,
  b.trx_id blocking_trx_id,
  b.trx_mysql_thread_id blocking_thread,
  b.trx_query blocking_query
FROM performance_schema.data_lock_waits w
JOIN information_schema.INNODB_TRX b ON b.trx_id = w.blocking_engine_transaction_id
JOIN information_schema.INNODB_TRX r ON r.trx_id = w.requesting_engine_transaction_id;

-- 找到阻塞源后kill:
-- KILL blocking_thread;
```
