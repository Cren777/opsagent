# MySQL 备份与恢复

## 逻辑备份（mysqldump）

### 全量备份
```bash
# 单库备份
mysqldump -u root -p --single-transaction --routines --triggers \
  ops_agent > ops_agent_$(date +%Y%m%d).sql

# 全部数据库
mysqldump -u root -p --all-databases --single-transaction > all_db.sql
```

### 备份策略
| 频率 | 类型 | 说明 |
|------|------|------|
| 每日 | 全量备份 | 非高峰期（凌晨2-4点） |
| 每小时 | 增量备份 | binlog 备份 |
| 每周 | 异地备份 | 将备份传输至异地 |

## 物理备份

### XtraBackup（推荐）
```bash
# 全量备份
xtrabackup --backup --user=root --password=xxx --target-dir=/backup/full

# 增量备份
xtrabackup --backup --user=root --password=xxx \
  --target-dir=/backup/inc1 --incremental-basedir=/backup/full
```

## 恢复数据

### mysqldump 恢复
```bash
mysql -u root -p ops_agent < ops_agent_20260501.sql
```

### 时间点恢复（PITR）
```bash
# 1. 恢复最近的全量备份
# 2. 应用binlog到指定时间点
mysqlbinlog --stop-datetime="2026-05-15 10:00:00" \
  mysql-bin.000001 mysql-bin.000002 | mysql -u root -p
```

## 主从复制

### 查看复制状态
```sql
SHOW SLAVE STATUS\G
-- 关键指标：
-- Slave_IO_Running: Yes（IO线程，从master读取binlog）
-- Slave_SQL_Running: Yes（SQL线程，回放binlog）
-- Seconds_Behind_Master: < 10（复制延迟）
```

### 主从延迟排查
1. 检查 Slave_SQL_Running 是否为 Yes
2. 查看 Seconds_Behind_Master（秒数）
3. 检查从库硬件资源（CPU/IO）
4. 检查是否存在大事务
5. 考虑并行复制：`SET GLOBAL slave_parallel_workers = 4;`

### 跳过错误
```sql
-- 跳过当前错误（谨慎使用）
SET GLOBAL SQL_SLAVE_SKIP_COUNTER = 1;
START SLAVE;
```
