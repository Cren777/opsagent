# Linux 进程管理

## 查看进程

### 查看所有进程
```bash
ps aux          # 显示所有进程
ps -ef          # 另一种格式
pstree -p       # 树形显示进程关系
```

### 实时监控进程
```bash
top             # 实时进程监控
htop            # 更友好的交互式监控（需单独安装）
```

常用 top 交互命令：
- `1`：展开/折叠CPU核心
- `M`：按内存使用排序
- `P`：按CPU使用排序
- `k`：杀死进程（输入PID）
- `q`：退出

## 查找进程
```bash
pgrep nginx             # 按名称查找PID
pidof nginx             # 同功能
ps -C nginx             # 按名称筛选
ps aux | grep nginx     # 管道方式查找
```

## 杀死进程
```bash
kill PID           # 发送 TERM 信号（优雅退出）
kill -9 PID        # 强制杀死（SIGKILL）
kill -15 PID       # 默认信号（SIGTERM）
killall nginx      # 按名称杀死所有匹配进程
pkill -f nginx     # 模糊匹配进程名
```

## 进程优先级管理
```bash
nice -n -10 nginx        # 以高优先级启动进程
renice -n 5 -p 12345     # 调整现有进程优先级
```

### 优先级范围
- -20（最高优先级）到 19（最低优先级）
- 普通用户只能降低优先级（增大nice值）
- root用户可以设置任何优先级

## 故障排查

### CPU 使用率过高
```bash
# 1. 找到高CPU佔用进程
top -bn1 | head -20

# 2. 查看该进程的线程
top -H -p PID

# 3. 分析线程栈
strace -p PID -c     # 统计系统调用
perf top -p PID       # 实时性能分析
```

### 常见原因
1. **死循环/无限循环**：代码bug导致CPU持续高负载
2. **GC频繁**：Java应用内存不足导致Full GC频繁
3. **并发连接过多**：处理大量请求
4. **CPU密集型批处理任务**：大数据计算
