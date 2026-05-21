# systemd 服务管理

## 基本命令

### 服务状态管理
```bash
systemctl start nginx        # 启动服务
systemctl stop nginx         # 停止服务
systemctl restart nginx      # 重启服务
systemctl reload nginx       # 重载配置（不中断服务）
systemctl status nginx       # 查看服务状态
systemctl enable nginx       # 开机自启
systemctl disable nginx      # 禁止自启
systemctl is-active nginx    # 是否运行中
systemctl is-enabled nginx   # 是否开机自启
```

### 查看日志
```bash
journalctl -u nginx                    # 查看nginx日志
journalctl -u nginx -f                 # 实时跟踪
journalctl -u nginx --since "1 hour ago"  # 查看最近1小时
journalctl -u nginx -p err             # 只看ERROR级别
journalctl -u nginx --since today      # 今天以来的日志
```

### 列出所有服务
```bash
systemctl list-units --type=service          # 所有活动的服务
systemctl list-units --type=service --all    # 所有服务（含未运行）
systemctl list-unit-files --type=service     # 所有已安装的服务文件
```

## 自定义 Service 文件

### 标准模板
```ini
[Unit]
Description=My Application Service
After=network.target

[Service]
Type=simple
User=appuser
Group=appgroup
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/java -jar /opt/myapp/app.jar
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## 服务启动失败排查

### 步骤一：查看状态
```bash
systemctl status nginx
# 关注: Loaded, Active, Process, Main PID

### 步骤二：查看日志
```bash
journalctl -u nginx -n 50 --no-pager
```

### 步骤三：验证配置文件
```bash
nginx -t                    # 测试nginx配置
apache2ctl configtest       # 测试apache配置
```

### 步骤四：手动启动调试
```bash
# 直接运行启动命令，查看报错
/usr/sbin/nginx
```

### 常见失败原因
1. 配置文件语法错误
2. 端口被占用（Address already in use）
3. 依赖服务未启动（After=配置）
4. 权限不足（Permission denied）
5. 文件路径不存在或无访问权限
6. PID文件残留（删除.pid文件后重启）
