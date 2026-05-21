#!/usr/bin/env python3
"""演示场景执行脚本"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from ops_agent.core.orchestrator import Orchestrator
from ops_agent.utils.logging_config import setup_logging

setup_logging("WARNING")

DEMO_QUERIES = [
    ("知识查询", "如何查看磁盘使用率？"),
    ("知识查询", "数据库连接数满了怎么处理？"),
    ("知识查询", "nginx服务无法启动怎么排查？"),
    ("数据分析", "最近一周有哪些critical告警？"),
    ("数据分析", "每个服务器上运行了多少个服务？"),
    ("数据分析", "过去7天工单平均处理时间是多少？"),
    ("故障排查", "web-01服务器CPU使用率100%，帮我排查"),
    ("故障排查", "系统日志中出现大量Permission denied错误"),
]


async def run_demos():
    orchestrator = Orchestrator()
    passed = 0
    failed = 0

    print("=" * 60)
    print("  OpsAgent 演示场景测试")
    print("=" * 60)

    for i, (category, query) in enumerate(DEMO_QUERIES, 1):
        print(f"\n{'─' * 60}")
        print(f"[{i}/{len(DEMO_QUERIES)}] [{category}] {query}")
        print(f"{'─' * 60}")

        try:
            start = time.time()
            result = await orchestrator.process(query)
            elapsed = time.time() - start

            answer = result.get("answer", "")
            intent = result.get("intent", "")
            print(f"  意图: {intent} | 耗时: {elapsed:.1f}s")
            print(f"  回答: {answer[:200]}...")
            if result.get("sql"):
                print(f"  SQL: {result['sql']}")
            if result.get("sources"):
                print(f"  来源: {[s['title'] for s in result['sources']]}")

            if answer and len(answer) > 10:
                passed += 1
                print(f"  ✅ 通过")
            else:
                failed += 1
                print(f"  ❌ 回答过短或为空")
        except Exception as e:
            failed += 1
            print(f"  ❌ 异常: {e}")

    print(f"\n{'=' * 60}")
    print(f"  结果: {passed} 通过, {failed} 失败 (共 {len(DEMO_QUERIES)} 项)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_demos())
