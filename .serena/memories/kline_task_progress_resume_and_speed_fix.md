# K线任务进度恢复和下载速度计算修复

## 问题1：任务进度恢复

### 问题描述
重启系统后任务无法基于之前的进度继续，总是从头开始。

### 根本原因
1. ImportProgress类缺少processed_symbols_list字段来记录已处理的股票列表
2. _execute_task方法启动任务时没有检查已保存的进度
3. 任务总是从头开始，不会跳过已处理的股票

### 修复方案
1. 在ImportProgress类中添加processed_symbols_list字段（List[str]）
2. 在_import_kline_data中实时更新进度时保存已处理的股票列表
3. 在_execute_task开始时检查已保存的进度，如果有RUNNING状态的进度，则：
   - 恢复已处理的记录数
   - 从原始股票列表中过滤掉已处理的股票
   - 只处理剩余的股票
4. 在TaskExecutionResult中也添加processed_symbols_list字段

## 问题2：下载速度显示为0

### 问题描述
K线下载情况中的下载速度一直显示为0。

### 根本原因
1. RealtimeWriteMonitoringWidget的update_progress方法没有计算速度
2. speed_label显示的是write_data中的speed值，但这个值从未被更新

### 修复方案
1. 在update_progress方法中添加速度计算逻辑
2. 从message中提取已处理的记录数（使用正则表达式匹配格式如"(50/100)"）
3. 基于时间间隔和记录数增量计算速度（记录数/秒）
4. 使用指数移动平均平滑速度，避免抖动
5. 根据速度值动态调整颜色（绿色>10条/秒，蓝色>5条/秒，橙色<5条/秒）

## 修改的文件
1. core/importdata/import_config_manager.py - 添加processed_symbols_list字段
2. core/importdata/import_execution_engine.py - 添加进度恢复逻辑和速度计算
3. gui/widgets/realtime_write_ui_components.py - 添加下载速度计算和显示