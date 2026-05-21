# Linux 网络诊断

## 网络连通性测试
```bash
ping -c 4 8.8.8.8              # ICMP连通性测试
traceroute www.example.com      # 路由追踪
mtr www.example.com             # 动态路由追踪（ping+traceroute）
telnet 192.168.1.1 80           # 测试TCP端口连通性
nc -zv 192.168.1.1 3306         # 端口扫描
```

## 查看网络状态
```bash
ip addr show                    # 查看IP地址
ip route show                   # 查看路由表
ss -tlnp                        # 查看TCP监听端口
ss -tunap                       # 查看所有TCP/UDP连接
netstat -i                      # 查看网络接口统计
```

## DNS 诊断
```bash
nslookup www.example.com        # DNS解析测试
dig www.example.com +short      # 详细DNS查询
host www.example.com            # 简洁DNS查询
cat /etc/resolv.conf            # 查看DNS配置
```

## 网络故障排查流程

### 1. 检查物理层
```bash
ip link show                    # 检查网卡状态（UP/DOWN）
ethtool eth0                    # 查看网卡详细信息
dmesg | grep -i eth             # 查看网卡驱动日志
```

### 2. 检查IP层
```bash
ip addr show eth0               # 检查IP配置
ip neigh show                   # ARP表
iptables -L -n -v               # 查看防火墙规则
```

### 3. 检查传输层
```bash
ss -tlnp                        # 检查服务监听状态
ss -s                           # 统计信息
```

### 4. Packet Loss排查
```bash
# MTR报告解读
# Loss% - 丢包率
# Avg   - 平均延迟
# Best/Worst - 最佳/最差延迟
# StDev - 延迟抖动（标准差 > 平均延迟说明网络不稳定）
```

## 常见网络问题

| 症状 | 可能原因 | 排查命令 |
|------|---------|---------|
| 无法访问外网 | DNS/网关配置错误 | `ip route`, `cat /etc/resolv.conf` |
| 端口不通 | 防火墙/服务未启动 | `iptables -L`, `ss -tlnp` |
| 延迟高 | 网络拥塞/路由绕路 | `mtr`, `ping` |
| 丢包严重 | 网卡故障/带宽不足 | `ethtool`, `netstat -i` |
| connection refused | 服务未监听该端口 | `ss -tlnp` |
| connection timeout | 防火墙丢弃SYN包 | `iptables -L -n` |
