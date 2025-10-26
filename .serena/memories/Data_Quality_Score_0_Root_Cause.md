## 问题
数据质量评分为 0.0 导致故障转移失败的根本原因：

1. **直接原因**：AKSharePlugin.get_kdata() 返回空 DataFrame
2. **设计问题**：AKShare 插件被标记为"暂不实现K线数据"，因为主要用于板块资金流
3. **触发链条**：
   - 调用 get_kline_data() 请求K线数据
   - 系统转换为 get_kdata() 调用 AKSharePlugin
   - 返回空 DataFrame → 数据质量评分 = 0.0（见 tet_data_pipeline.py 第1111-1112行）
   - 评分 0.0 < 0.7 阈值 → 故障转移失败，记录：'数据质量不合格: 0.0'

## 解决方案
1. **AKSharePlugin**：实现 get_kdata() 方法，使用 ak.stock_zh_a_hist() API
   - 参数转换：freq → period (D/W/M → daily/weekly/monthly)
   - 符号处理：移除后缀 (000001.SZ → 000001)
   - 日期转换：YYYY-MM-DD → YYYYMMDD
   - 返回标准格式 DataFrame（日期索引、OHLCV列）

2. **检查其他插件**：
   - YahooFinanceDataSourcePlugin：get_kdata() 未实现（TODO注释）
   - CryptoUniversalPlugin：get_kdata() 返回空 DataFrame
   - Level2RealtimePlugin：正确返回空 DataFrame + 警告日志

## 关键改进
- AKShare 现在能真正获取 K线数据（不再返回空 DataFrame）
- 数据质量评分不再为 0.0（有实际数据时评分会正常计算）
- 故障转移机制能正常工作