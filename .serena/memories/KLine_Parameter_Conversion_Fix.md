## 问题
调用 get_kline_data() 时出现错误：`AKSharePlugin.get_kdata() got an unexpected keyword argument 'frequency'`

## 根本原因
1. 系统调用 get_kline_data() 方法，传递 frequency 参数
2. 当插件不支持该方法时，系统自动转换为替代方法名（如 get_kdata）
3. 问题在于参数映射只在 method_name == 'get_kline_data' 时进行
4. 当方法被转换为替代名称（如 get_kdata）后，参数映射条件不再满足
5. 因此 frequency 参数直接传递给 get_kdata()，而 get_kdata() 期望的是 freq 参数

## 解决方案
修改了 _execute_with_failover 方法中的参数映射逻辑，使其在检查替代方法后也能进行参数转换。

处理流程：
1. 当 method_name 为 'get_kdata' 或 'get_kline_data' 时
2. 检查是否有 frequency 参数
3. 对于 get_kdata：转换为 freq 参数
4. 对于 get_kline_data：转换为 period 参数

## 修改位置
core/services/uni_plugin_data_manager.py 第905-920行

## 测试结果
✓ 成功获取K线数据，通过故障转移机制找到了支持该功能的插件

## 关键改进
参数映射现在考虑了替代方法名的情况，确保无论使用哪个方法名，参数都能正确转换。