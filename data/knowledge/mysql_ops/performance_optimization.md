# MySQL 性能优化

## 慢查询分析

### 启用慢查询日志
```sql
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 2;          -- 超过2秒算慢查询
SET GLOBAL log_queries_not_using_indexes = ON;  -- 记录未使用索引的查询
```

### 分析慢查询
```bash
mysqldumpslow -s t -t 10 slow.log   # 按时间排序，显示top 10
pt-query-digest slow.log            # Percona工具，更详细的分析
```

### 查看当前运行的查询
```sql
SHOW FULL PROCESSLIST;               -- 查看所有连接和执行中的查询
SELECT * FROM information_schema.PROCESSLIST WHERE COMMAND != 'Sleep';
```

## 索引优化

### 查看索引使用情况
```sql
-- 查找未使用的索引
SELECT * FROM sys.schema_unused_indexes;

-- 查找冗余索引
SELECT * FROM sys.schema_redundant_indexes;

-- 查看表索引
SHOW INDEX FROM table_name;
```

### 索引优化原则
1. WHERE、JOIN、ORDER BY 字段应建索引
2. 高选择性的列优先（性别只有男女，不适合建索引）
3. 复合索引遵循最左前缀原则
4. 避免在索引列上使用函数（如 `WHERE YEAR(date_col) = 2025`）
5. 定期重建碎片化严重的索引：
```sql
ALTER TABLE table_name ENGINE=InnoDB;
OPTIMIZE TABLE table_name;
```

## 连接数管理

### 查看连接数
```sql
SHOW VARIABLES LIKE 'max_connections';     -- 最大连接数
SHOW STATUS LIKE 'Threads_connected';       -- 当前连接数
SHOW STATUS LIKE 'Max_used_connections';    -- 历史最高连接数
```

### 连接数满了怎么办
1. 临时提高最大连接数：
```sql
SET GLOBAL max_connections = 1000;
```
2. 检查是否有大量Sleep连接未释放
3. 检查应用连接池配置（如HikariCP maximumPoolSize）
4. 检查是否存在连接泄漏（长时间事务未提交）

## 锁与事务

### 查看锁等待
```sql
-- MySQL 8.0+
SELECT * FROM performance_schema.data_lock_waits;

-- 查看InnoDB锁
SHOW ENGINE INNODB STATUS\G

-- 查看未提交事务
SELECT * FROM information_schema.INNODB_TRX;
```

### 死锁排查
```bash
# 查看最近一次死锁信息
SHOW ENGINE INNODB STATUS\G | grep -A 30 "LATEST DETECTED DEADLOCK"
```

## 内存优化

### InnoDB Buffer Pool
```sql
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
-- 建议设置为物理内存的60%-80%
```

### 查看Buffer Pool命中率
```sql
SELECT
  (1 - (SELECT VARIABLE_VALUE FROM performance_schema.global_status
        WHERE VARIABLE_NAME='Innodb_buffer_pool_reads') /
       (SELECT VARIABLE_VALUE FROM performance_schema.global_status
        WHERE VARIABLE_NAME='Innodb_buffer_pool_read_requests')) * 100
AS buffer_pool_hit_rate;
-- 命中率应 > 99%
```
