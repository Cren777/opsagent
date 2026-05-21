#!/bin/bash
# 内存使用情况检查
echo "=== 内存使用概况 ==="
free -h 2>/dev/null || echo "[模拟] free 命令不可用"
echo ""
echo "=== 高内存进程 Top 5 ==="
ps aux --sort=-%mem 2>/dev/null | head -6 || echo "[模拟] ps 不可用"
echo ""
echo "=== Swap 使用情况 ==="
swapon --show 2>/dev/null || echo "[模拟] swap 信息不可用"
echo ""
echo "=== /proc/meminfo (关键项) ==="
if [ -f /proc/meminfo ]; then
    grep -E "^(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree)" /proc/meminfo
else
    echo "[模拟] /proc/meminfo 不可用"
fi
