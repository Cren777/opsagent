"""Pytest fixtures"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 测试数据：15个测试查询及其预期意图
TEST_QUERIES = [
    # (query, expected_intent)
    ("如何查看磁盘使用率？", "knowledge_query"),
    ("最近一周有哪些critical告警？", "data_analysis"),
    ("web-01服务器CPU使用率100%，帮我排查", "fault_troubleshooting"),
    ("数据库连接数满了怎么处理？", "knowledge_query"),
    ("每个服务器上运行了多少个服务？", "data_analysis"),
    ("系统日志中出现大量Permission denied错误", "fault_troubleshooting"),
    ("过去7天工单平均处理时间是多少？", "data_analysis"),
    ("nginx服务无法启动怎么排查？", "knowledge_query"),
    ("统计每个部门的工单数量", "data_analysis"),
    ("磁盘空间不足如何处理", "knowledge_query"),
    ("怎么杀进程？", "knowledge_query"),
    ("app-01内存不足", "fault_troubleshooting"),
    ("查询所有在线的服务器", "data_analysis"),
    ("mysql主从复制延迟怎么修复", "knowledge_query"),
    ("CPU异常高温，服务响应慢", "fault_troubleshooting"),
]
