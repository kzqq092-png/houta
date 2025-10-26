## 最终问题分析和解决方案

### 问题链条
1. 用户请求获取 K线数据：000002 symbol
2. 系统调用 get_kline_data()
3. 系统转换为 get_kdata() 调用各个插件
4. **AKSharePlugin.get_kdata() 返回空 DataFrame (pd.DataFrame())** 
5. TETDataPipeline 计算数据质量评分：空 DataFrame = 0.0 分 (tet_data_pipeline.py 第1111-1112行)
6. 质量分数 0.0 < 0.7 阈值 → 插件被标记为故障
7. 全部插件失败 → 故障转移失败，错误信息："所有插件都无法提供有效数据...数据质量不合格: 0.0"

### 根本原因
**AKSharePlugin 被设计为只提供板块资金流数据，不提供 K线数据**
- 注释说明：第436行"AKShare插件主要用于板块资金流，暂不实现K线数据"
- 但系统在"历史K线"数据类型下仍然尝试调用它
- 导致返回空 DataFrame，质量评分为 0.0

### 解决方案
在 AKSharePlugin.get_kdata() 中实现真实的 K线数据获取：
- 使用 AKShare 库提供的 `ak.stock_zh_a_hist()` API
- 参数转换：
  - freq: D→daily, W→weekly, M→monthly
  - 符号: 000001.SZ → 000001（移除后缀）
  - 日期: YYYY-MM-DD → YYYYMMDD
- 列名标准化：将中文列名映射到英文
- 返回标准 DataFrame（datetime索引、OHLCV列）

### 修改位置
- plugins/data_sources/stock/akshare_plugin.py （get_kdata 方法，第433-537行）

### 测试结果
✓ AKShare 单元测试：获取 16 条日线记录，5 条周线记录
✓ 端到端集成测试：成功获取 K线数据，数据质量评分正常（>0）
✓ 故障转移机制正常工作

### 其他发现
- YahooFinanceDataSourcePlugin：get_kdata() 未实现（TODO注释）
- CryptoUniversalPlugin：get_kdata() 返回空 DataFrame（预期设计）
- Level2RealtimePlugin：正确返回空 + 警告日志（预期设计）