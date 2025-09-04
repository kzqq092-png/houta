# 回测系统深度分析报告
==================================================

## 分析摘要
- 分析耗时: 1.46 秒
- 发现问题: 336 个
- 严重问题: 4 个
- 性能瓶颈: 1 个

## 静态代码分析
- 分析文件数: 8
- 发现问题数: 330

### 主要问题:
- MINOR: 函数 backtest_strategy_fixed 参数过多: 11 (backtest\unified_backtest_engine.py:972)
- MINOR: 函数 run_backtest 参数过多: 14 (backtest\unified_backtest_engine.py:152)
- MINOR: 函数 _run_core_backtest 参数过多: 13 (backtest\unified_backtest_engine.py:287)
- MINOR: 函数 _process_trading_signals 参数过多: 9 (backtest\unified_backtest_engine.py:398)
- MINOR: 函数 _calculate_unified_risk_metrics 过长: 109 行 (backtest\unified_backtest_engine.py:572)
- MAJOR: 使用了裸露的except语句 (backtest\unified_backtest_engine.py:702)
- MAJOR: 使用了裸露的except语句 (backtest\unified_backtest_engine.py:713)
- MAJOR: 使用了裸露的except语句 (backtest\unified_backtest_engine.py:723)
- MAJOR: 使用了裸露的except语句 (backtest\unified_backtest_engine.py:730)
- MAJOR: 使用了裸露的except语句 (backtest\unified_backtest_engine.py:751)

## 性能分析
- 数据加载: 0.0023秒 (吞吐量: 158146 记录/秒)
- 策略执行: 0.0427秒 (吞吐量: 8554 信号/秒)

### 性能瓶颈:
- strategy_execution: 0.0427秒 (90.7%)