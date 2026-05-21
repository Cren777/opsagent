# Linux 磁盘管理

## 查看磁盘使用情况
```bash
df -h           # 查看分区使用情况
df -i           # 查看inode使用情况
du -sh /var/*   # 查看目录磁盘占用
du -ah --max-depth=1 /home  # 按层级查看
```

## 查看磁盘和分区
```bash
lsblk           # 列出块设备
fdisk -l        # 查看分区表
blkid           # 查看分区UUID
ls -l /dev/sd*  # 查看磁盘设备文件
```

## 磁盘空间不足排查

### 步骤一：定位大文件
```bash
du -ah / | sort -rh | head -20           # 全局扫描（慢）
find / -type f -size +1G 2>/dev/null      # 查找大于1GB的文件
```

### 步骤二：检查已删除但未释放的文件
```bash
lsof | grep deleted    # 查看被删除但仍被进程占用的文件
lsof +L1               # 查看引用计数小于1的文件
```

### 步骤三：检查日志文件
```bash
ls -lhS /var/log/     # 按大小排序查看日志
journalctl --disk-usage  # 查看journal日志占用空间
journalctl --vacuum-size=500M  # 清理journal日志
```

### 步骤四：清理空间
```bash
# 清理apt/yum缓存
apt clean && apt autoclean
yum clean all

# 删除旧内核
dpkg -l | grep linux-image | grep -v $(uname -r)
package-cleanup --oldkernels --count=2

# 清理/tmp
find /tmp -type f -mtime +7 -delete
```

## 磁盘IO性能分析
```bash
iostat -x 1 3          # 查看磁盘IO统计（每1秒，共3次）
iotop                   # 按进程查看IO使用情况
```

### iostat 关键指标
- **%util**：磁盘繁忙时间百分比，接近100%表示IO饱和
- **await**：IO请求平均等待时间（ms）
- **svctm**：IO请求平均服务时间（ms）
- **r/s, w/s**：每秒读写次数

### 高IO Wait排查
1. 查看 `iostat` 定位高负载磁盘
2. 使用 `iotop -oP` 找到高IO进程
3. 分析该进程的IO模式（读/写/随机/顺序）
4. 优化策略：升级SSD、增加内存做缓存、优化SQL查询
