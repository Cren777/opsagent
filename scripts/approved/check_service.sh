#!/bin/bash
# 服务状态检查
SERVICE=${1:-nginx}
echo "=== ${SERVICE} 服务状态 ==="
systemctl status "${SERVICE}" 2>/dev/null || echo "[模拟] systemctl 不可用"
echo ""
echo "=== ${SERVICE} 进程 ==="
pgrep -a "${SERVICE}" 2>/dev/null || echo "[模拟] ${SERVICE} 进程未运行或 pgrep 不可用"
echo ""
echo "=== ${SERVICE} 端口监听 ==="
ss -tlnp | grep -i "${SERVICE}" 2>/dev/null || echo "[模拟] ss 不可用或端口未监听"
