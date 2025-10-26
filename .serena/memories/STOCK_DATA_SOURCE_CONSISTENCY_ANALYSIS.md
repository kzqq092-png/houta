## 股票数据源一致性分析 - 关键发现

### 官方数据（2024-03-31）
- 上证所(SH): 2,272 家上市公司
- 深证所(SZ): 2,851 家上市公司
- 合计: 5,123 家上市公司

### 通达信插件分析（TongdaxinStockPlugin）
**关键代码位置**: plugins/data_sources/stock/tongdaxin_plugin.py 第1158-1219行

**获取逻辑**:
- 上证: `api_client.get_security_count(1)` + `get_security_list(1, start)`
- 深证: `api_client.get_security_count(0)` + `get_security_list(0, start)`

### 发现的5个关键问题（按优先级排列）

**[CRITICAL-HIGH] 问题1: 数据截断（第1178、1191行）**
```python
for start in range(0, min(count, 10000), 1000):  # 限制最多10000
```
- 当真实数据>10000时触发，导致数据丢失
- 当前状态：SH(2272)和SZ(2851)都<10000，暂未触发
- 未来风险：HIGH（股票数增加时自动截断）

**[MEDIUM] 问题2: 连接管理不优化**
- 所有请求共用一个connection_lock
- 10+次API调用顺序执行，容易超时
- 单一失败导致整体失败

**[MEDIUM] 问题3: 错误处理不足**
- 统一try-except，无市场级别恢复
- SH获取失败会阻止SZ获取
- 应分离异常处理

**[LOW] 问题4: B股处理缺失**
- 900xxx(沪B)、200xxx(深B)处理不明确
- 可能导致分类不一致

**[LOW] 问题5: 缓存同步问题**
- 缓存过期设置不明确
- 无手动更新机制

### 数据不一致原因分析

**插件数据>官方数据** (概率中等):
- ST/退市股票被包含
- B股被计入
- 新股上市速度差异

**插件数据<官方数据** (概率高):
- 10000数据截断（主要风险）
- 网络超时中断
- 连接失败

### 改进建议优先级

1. **[HIGH]** 移除10000限制: `for start in range(0, count, 1000):`
2. **[MEDIUM]** 分市场错误处理
3. **[MEDIUM]** 并行获取(ThreadPoolExecutor)
4. **[LOW]** 分类统计输出
5. **[LOW]** 缓存策略优化