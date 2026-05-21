# Nginx 运维指南

## 基本管理
```bash
nginx -t                     # 测试配置文件
nginx -s reload              # 热重载配置
nginx -s stop                # 快速停止
nginx -s quit                # 优雅退出
```

## 常用配置

### 反向代理
```nginx
server {
    listen 80;
    server_name example.com;
    
    location / {
        proxy_pass http://backend_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 负载均衡
```nginx
upstream backend {
    least_conn;  # 最少连接算法
    server 192.168.1.10:8080 weight=5 max_fails=3 fail_timeout=30s;
    server 192.168.1.11:8080 weight=3;
    server 192.168.1.12:8080 backup;  # 备用
}
```

### HTTPS配置
```nginx
server {
    listen 443 ssl;
    server_name example.com;
    ssl_certificate     /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
}
```

## 常见故障排查

### 502 Bad Gateway
- 原因：nginx无法与后端服务通信
- 排查：
  1. 后端服务是否运行：`systemctl status backend`
  2. 后端端口是否监听：`ss -tlnp | grep backend_port`
  3. 防火墙是否阻止：`iptables -L -n`
  4. 查看nginx错误日志：`tail -f /var/log/nginx/error.log`

### 504 Gateway Timeout
- 原因：后端响应时间过长
- 解决：
  1. 增加proxy超时：
```nginx
proxy_connect_timeout 300s;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```
  2. 优化后端查询性能
  3. 考虑异步处理长时间任务

### 高并发优化
```nginx
worker_processes auto;
worker_connections 4096;
worker_rlimit_nofile 65535;

events {
    use epoll;
    multi_accept on;
}

http {
    keepalive_timeout 65;
    keepalive_requests 1000;
    gzip on;
    gzip_types text/plain application/json;
    sendfile on;
    tcp_nopush on;
}
```

### SSL证书过期
```bash
# 检查证书过期时间
openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -dates

# 更新 Let's Encrypt 证书
certbot renew --dry-run
certbot renew
```
