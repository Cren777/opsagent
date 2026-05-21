#!/bin/bash
# 磁盘使用情况检查
echo "=== 磁盘使用情况 ==="
df -h 2>/dev/null || echo "[模拟] df 命令在此环境不可用"
echo ""
echo "=== 大文件 Top 10 ==="
if [ -d /var/log ]; then
    du -sh /var/log/* 2>/dev/null | sort -rh | head -10
else
    echo "[模拟] /var/log 目录不存在"
fi
echo ""
echo "=== Inode 使用情况 ==="
df -i 2>/dev/null || echo "[模拟] df -i 不可用"
