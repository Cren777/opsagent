# 常见告警指标解读

## CPU 相关指标

### CPU使用率（user + system + iowait）
- **正常范围**：< 70%
- **告警阈值**：> 85% warning, > 95% critical
- **user高**：应用层计算密集
- **system高**：频繁系统调用，I/O操作过多
- **iowait高**：磁盘IO瓶颈

### Load Average
```bash
uptime
# 输出: load average: 1.50, 2.30, 3.10
# 含义: 1分钟、5分钟、15分钟的平均负载
```
- **判断标准**：load < CPU核心数（如8核则<8）
- **> CPU核心数**：系统过载
- **> 2x CPU核心数**：严重过载

## 内存相关指标

### 内存使用率
- **正常范围**：< 80%
- **告警阈值**：> 85% warning, > 95% critical
- **注意区分**：cached/buffers可释放内存
- **实际可用** = free + buffers + cached

### Swap使用
- **Swap > 0**：需要关注
- **Swap > 1GB**：内存不足，需扩容
- **频繁Swap in/out**：性能严重下降

## 磁盘相关指标

### 磁盘使用率
- **正常范围**：< 80%
- **告警阈值**：> 85% warning, > 90% critical
- **增长速率**：预测剩余天数

### 磁盘IO
- **%util > 90%**：磁盘IO饱和
- **await > 30ms**：IO延迟过高
- **queue size > 5**：IO请求排队严重

## 网络相关指标

### 带宽使用率
- **< 70%**：正常
- **> 85%**：需要扩容

### 网络错误率
- **> 1%**：网络质量问题
- **packet loss > 0.1%**：丢包严重

### TCP连接数
- **ESTABLISHED 连接数过高**：可能遭受攻击或连接泄漏
- **TIME_WAIT 大量堆积**：需调整内核参数
