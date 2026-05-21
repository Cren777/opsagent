#!/bin/bash
# CPU 使用情况检查
echo "=== CPU 使用率 ==="
top -bn1 | head -5 2>/dev/null || echo "[模拟] top 命令输出不可用"
echo ""
echo "=== Load Average ==="
uptime 2>/dev/null || echo "[模拟] uptime 不可用"
echo ""
echo "=== CPU 核心数 ==="
nproc 2>/dev/null || echo "[模拟] nproc 不可用 (模拟: 8 核)"
echo ""
echo "=== 高 CPU 进程 Top 5 ==="
ps aux --sort=-%cpu 2>/dev/null | head -6 || echo "[模拟] ps 不可用"
