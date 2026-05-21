# Docker 基础运维

## 容器管理
```bash
docker ps                          # 运行中的容器
docker ps -a                       # 所有容器
docker start|stop|restart <id>     # 启停
docker rm <id>                     # 删除容器
docker rm -f <id>                  # 强制删除运行中的容器
docker exec -it <id> /bin/bash     # 进入容器
docker logs <id>                   # 查看日志
docker logs -f --tail 100 <id>     # 实时查看最近100行
docker stats                       # 实时资源使用
```

## 镜像管理
```bash
docker images                      # 列出镜像
docker pull nginx:latest           # 拉取镜像
docker rmi <image_id>              # 删除镜像
docker build -t myapp:v1 .         # 构建镜像
docker tag myapp:v1 myapp:latest   # 打标签
```

## Docker Compose
```yaml
version: '3.8'
services:
  nginx:
    image: nginx:1.24
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    restart: always
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
    volumes:
      - mysql_data:/var/lib/mysql
volumes:
  mysql_data:
```

## 资源限制

### 内存限制
```bash
docker run -m 512m --memory-swap 1g nginx
```

### CPU限制
```bash
docker run --cpus="1.5" nginx           # 最多使用1.5个核
docker run --cpuset-cpus="0-2" nginx    # 绑定核心0-2
```

## 常见问题

### 容器无法启动
```bash
# 查看退出原因
docker logs <container_id>

# 常见原因：
# - 端口冲突
# - 挂载卷权限问题
# - 环境变量错误
# - 内存不足
```

### 磁盘空间清理
```bash
docker system prune -a        # 清理所有未使用资源
docker volume prune           # 清理未使用卷
docker image prune -a         # 清理未使用镜像
```

### 容器内无法连接宿主机
```bash
# Mac/Windows: 使用 host.docker.internal
# Linux: 使用 --network host 或 172.17.0.1
# 或使用 host 网络模式:
docker run --network host nginx
```
