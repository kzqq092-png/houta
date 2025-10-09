
# 数据源降级配置
DATA_SOURCE_FALLBACK = {
    "stock_list": [
        "local_cache",      # 优先使用本地缓存
        "duckdb",          # 其次使用DuckDB
        "mock_data"        # 最后使用模拟数据
    ],
    "realtime_quotes": [
        "local_cache",
        "mock_data"
    ],
    "kline_data": [
        "local_cache", 
        "duckdb",
        "mock_data"
    ]
}

def get_fallback_stock_list():
    """获取降级股票列表"""
    import pandas as pd
    
    # 生成基本的A股股票列表
    stock_codes = []
    
    # 沪市主板 (600000-603999)
    for i in range(600000, 600100):  # 简化版本，只生成100个
        stock_codes.append(f"{i:06d}.SH")
    
    # 深市主板 (000001-000999)  
    for i in range(1, 100):  # 简化版本
        stock_codes.append(f"{i:06d}.SZ")
        
    # 创建DataFrame
    df = pd.DataFrame({
        'code': stock_codes,
        'name': [f'股票{i:04d}' for i in range(len(stock_codes))],
        'market': ['SH' if code.endswith('.SH') else 'SZ' for code in stock_codes]
    })
    
    return df

def get_fallback_realtime_quotes(codes):
    """获取降级实时行情"""
    import pandas as pd
    import random
    
    data = []
    for code in codes[:10]:  # 限制数量
        data.append({
            'code': code,
            'name': f'股票{code[:6]}',
            'price': round(random.uniform(10, 100), 2),
            'change': round(random.uniform(-5, 5), 2),
            'change_pct': round(random.uniform(-10, 10), 2),
            'volume': random.randint(1000000, 100000000),
            'amount': random.randint(10000000, 1000000000)
        })
    
    return pd.DataFrame(data)
