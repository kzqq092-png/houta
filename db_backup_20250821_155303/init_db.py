import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'factorweave_system.db')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 初始化插件数据库表
    try:
        from db.models.plugin_models import PluginDatabaseManager
        plugin_db = PluginDatabaseManager(DB_PATH)
        print("插件数据库表初始化完成")
    except Exception as e:
        print(f"插件数据库表初始化失败: {e}")
    # 1. 系统配置表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    # 2. 数据源表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS data_source (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        type TEXT,
        config TEXT,
        is_active INTEGER DEFAULT 0
    )''')
    # 3. 用户收藏表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        fav_type TEXT,
        fav_key TEXT,
        fav_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 4. 行业表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS industry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        parent_id INTEGER,
        level INTEGER,
        extra TEXT
    )''')
    # 5. 市场表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        code TEXT UNIQUE,
        region TEXT,
        extra TEXT
    )''')
    # 6. 股票表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        market_code TEXT,
        type TEXT,
        valid INTEGER,
        start_date TEXT,
        end_date TEXT,
        industry_id INTEGER,
        extra TEXT
    )''')
    # 7. 概念表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS concept (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        extra TEXT
    )''')
    # 8. 指标表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        params TEXT,
        extra TEXT
    )''')
    # 9. 用户日志表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT,
        detail TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 10. 历史记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        record_type TEXT,
        record_key TEXT,
        record_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # 11. 指标组合表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicator_combination (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        user_id TEXT,
        indicators TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        extra TEXT
    )''')
    # 12. 主题表（合并自themes.db）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS themes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        type TEXT,
        content TEXT,
        origin TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')

    # 13. 形态模式表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pattern_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        english_name TEXT,
        category TEXT NOT NULL,
        signal_type TEXT,
        description TEXT,
        min_periods INTEGER DEFAULT 5,
        max_periods INTEGER DEFAULT 60,
        confidence_threshold REAL DEFAULT 0.5,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 插入行业标准形态类型数据
    patterns_data = [
        # 反转形态 - 顶部
        ('双顶', 'double_top', '反转形态', 'sell',
         '双顶是一种看跌反转形态，当价格形成两个相近的高点后，通常会向下突破', 15, 40, 0.6, 1),
        ('头肩顶', 'head_shoulders_top', '反转形态', 'sell',
         '头肩顶是最可靠的看跌反转形态，由左肩、头部、右肩三个高点组成', 20, 60, 0.7, 1),
        ('三重顶', 'triple_top', '反转形态', 'sell',
         '三重顶由三个相近的高点组成，是强烈的看跌信号', 25, 50, 0.65, 1),
        ('圆弧顶', 'rounding_top', '反转形态', 'sell',
         '价格缓慢形成圆弧状的顶部，表示上升趋势即将结束', 30, 80, 0.6, 1),
        ('岛形反转顶', 'island_reversal_top', '反转形态', 'sell',
         '价格在高位形成跳空缺口后再次跳空下跌的形态', 5, 15, 0.8, 1),

        # 反转形态 - 底部
        ('双底', 'double_bottom', '反转形态', 'buy',
         '双底是一种看涨反转形态，当价格形成两个相近的低点后，通常会向上突破', 15, 40, 0.6, 1),
        ('头肩底', 'head_shoulders_bottom', '反转形态', 'buy',
         '头肩底是最可靠的看涨反转形态，由左肩、头部、右肩三个低点组成', 20, 60, 0.7, 1),
        ('三重底', 'triple_bottom', '反转形态', 'buy',
         '三重底由三个相近的低点组成，是强烈的看涨信号', 25, 50, 0.65, 1),
        ('圆弧底', 'rounding_bottom', '反转形态', 'buy',
         '价格缓慢形成圆弧状的底部，表示下降趋势即将结束', 30, 80, 0.6, 1),
        ('岛形反转底', 'island_reversal_bottom', '反转形态',
         'buy', '价格在低位形成跳空缺口后再次跳空上涨的形态', 5, 15, 0.8, 1),
        ('潜在双底', 'potential_double_bottom', '反转形态',
         'buy', '正在形成中的双底形态，需要确认突破', 10, 30, 0.5, 1),

        # 整理形态
        ('上升三角形', 'ascending_triangle', '整理形态', 'buy',
         '价格高点连线水平，低点连线上升，通常向上突破', 15, 40, 0.6, 1),
        ('下降三角形', 'descending_triangle', '整理形态', 'sell',
         '价格低点连线水平，高点连线下降，通常向下突破', 15, 40, 0.6, 1),
        ('对称三角形', 'symmetrical_triangle', '整理形态', 'neutral',
         '价格高点下降，低点上升，形成楔形，突破方向不确定', 15, 40, 0.5, 1),
        ('扩散三角形', 'expanding_triangle', '整理形态', 'neutral',
         '价格波动幅度逐渐扩大，市场不确定性增加', 20, 50, 0.4, 1),
        ('矩形整理', 'rectangle', '整理形态', 'neutral',
         '价格在水平的支撑阻力区间内震荡整理', 10, 30, 0.5, 1),
        ('楔形上升', 'rising_wedge', '整理形态', 'sell',
         '价格上涨但成交量递减，通常是看跌信号', 15, 35, 0.6, 1),
        ('楔形下降', 'falling_wedge', '整理形态', 'buy',
         '价格下跌但成交量递减，通常是看涨信号', 15, 35, 0.6, 1),
        ('旗形', 'flag', '整理形态', 'neutral', '短期内价格小幅震荡的整理形态', 5, 15, 0.5, 1),
        ('三角旗形', 'pennant', '整理形态', 'neutral', '类似三角形的短期整理形态', 5, 15, 0.5, 1),

        # 单根K线形态
        ('锤头线', 'hammer', '单根K线', 'buy', '实体小，下影线长，出现在下跌趋势中是看涨信号', 1, 1, 0.6, 1),
        ('上吊线', 'hanging_man', '单根K线', 'sell',
         '实体小，下影线长，出现在上涨趋势中是看跌信号', 1, 1, 0.6, 1),
        ('倒锤头', 'inverted_hammer', '单根K线', 'buy',
         '实体小，上影线长，出现在下跌趋势中是看涨信号', 1, 1, 0.6, 1),
        ('流星线', 'shooting_star', '单根K线', 'sell',
         '实体小，上影线长，出现在上涨趋势中是看跌信号', 1, 1, 0.6, 1),
        ('十字星', 'doji', '单根K线', 'neutral', '开盘价与收盘价相近，表示市场犹豫不决', 1, 1, 0.4, 1),
        ('长十字星', 'long_legged_doji', '单根K线', 'neutral',
         '上下影线都很长的十字星，市场极度不确定', 1, 1, 0.5, 1),
        ('蜻蜓十字星', 'dragonfly_doji', '单根K线', 'buy',
         '只有下影线的十字星，在底部是看涨信号', 1, 1, 0.6, 1),
        ('墓碑十字星', 'gravestone_doji', '单根K线', 'sell',
         '只有上影线的十字星，在顶部是看跌信号', 1, 1, 0.6, 1),
        ('光头光脚阳线', 'white_marubozu', '单根K线',
         'buy', '没有上下影线的阳线，表示强烈的买盘', 1, 1, 0.7, 1),
        ('光头光脚阴线', 'black_marubozu', '单根K线',
         'sell', '没有上下影线的阴线，表示强烈的卖盘', 1, 1, 0.7, 1),
        ('纺锤线', 'spinning_top', '单根K线', 'neutral',
         '实体小，上下影线长，表示多空力量均衡', 1, 1, 0.3, 1),

        # 双根K线形态
        ('看涨吞没', 'bullish_engulfing', '双根K线', 'buy',
         '大阳线完全吞没前一根阴线，强烈看涨信号', 2, 2, 0.7, 1),
        ('看跌吞没', 'bearish_engulfing', '双根K线', 'sell',
         '大阴线完全吞没前一根阳线，强烈看跌信号', 2, 2, 0.7, 1),
        ('刺透形态', 'piercing_pattern', '双根K线', 'buy',
         '阳线向上刺透前一根阴线实体的一半以上', 2, 2, 0.6, 1),
        ('乌云盖顶', 'dark_cloud_cover', '双根K线', 'sell',
         '阴线向下覆盖前一根阳线实体的一半以上', 2, 2, 0.6, 1),
        ('孕线形态', 'harami', '双根K线', 'neutral',
         '小K线被包含在大K线实体内，表示趋势可能转变', 2, 2, 0.5, 1),
        ('十字孕线', 'harami_cross', '双根K线', 'neutral',
         '十字星被包含在前一根大K线内，转向信号更强', 2, 2, 0.6, 1),

        # 三根K线形态
        ('早晨之星', 'morning_star', '三根K线', 'buy',
         '阴线+小实体+阳线的组合，底部反转信号', 3, 3, 0.7, 1),
        ('黄昏之星', 'evening_star', '三根K线', 'sell',
         '阳线+小实体+阴线的组合，顶部反转信号', 3, 3, 0.7, 1),
        ('早晨十字星', 'morning_doji_star', '三根K线', 'buy',
         '阴线+十字星+阳线的组合，强烈底部反转信号', 3, 3, 0.8, 1),
        ('黄昏十字星', 'evening_doji_star', '三根K线', 'sell',
         '阳线+十字星+阴线的组合，强烈顶部反转信号', 3, 3, 0.8, 1),
        ('三白兵', 'three_white_soldiers', '三根K线',
         'buy', '三根连续上涨的阳线，强烈看涨信号', 3, 3, 0.7, 1),
        ('三只乌鸦', 'three_black_crows', '三根K线',
         'sell', '三根连续下跌的阴线，强烈看跌信号', 3, 3, 0.7, 1),
        ('红三兵', 'three_advancing_soldiers', '三根K线',
         'buy', '三根逐步上涨的阳线，稳健看涨信号', 3, 3, 0.6, 1),
        ('三个内部上升', 'three_inside_up', '三根K线',
         'buy', '看涨孕线后跟随一根确认阳线', 3, 3, 0.6, 1),
        ('三个内部下降', 'three_inside_down', '三根K线',
         'sell', '看跌孕线后跟随一根确认阴线', 3, 3, 0.6, 1),
        ('弃婴形态', 'abandoned_baby', '三根K线', 'neutral',
         '中间K线与两侧K线都有跳空，强烈反转信号', 3, 3, 0.8, 1),

        # 多根K线复合形态
        ('塔形顶', 'tower_top', '多根K线', 'sell', '长阳线后经过整理再出现长阴线的顶部形态', 5, 15, 0.6, 1),
        ('塔形底', 'tower_bottom', '多根K线', 'buy',
         '长阴线后经过整理再出现长阳线的底部形态', 5, 15, 0.6, 1),
        ('上升通道', 'rising_channel', '多根K线', 'buy',
         '价格在上升趋势线和平行线之间运行', 10, 50, 0.5, 1),
        ('下降通道', 'falling_channel', '多根K线', 'sell',
         '价格在下降趋势线和平行线之间运行', 10, 50, 0.5, 1),
        ('喇叭形', 'megaphone', '多根K线', 'neutral', '价格波动幅度逐渐扩大的形态', 15, 40, 0.4, 1),
        ('钻石形', 'diamond', '多根K线', 'neutral', '先扩散后收敛的菱形整理形态', 20, 60, 0.5, 1),
        ('杯柄形态', 'cup_and_handle', '多根K线', 'buy',
         'U形底部后的小幅整理，长期看涨形态', 30, 100, 0.6, 1),
        ('碟形整理', 'saucer', '多根K线', 'buy', '长期的圆弧底形态，温和的看涨信号', 40, 120, 0.5, 1),

        # 缺口形态
        ('向上跳空', 'gap_up', '缺口形态', 'buy', '开盘价高于前一日最高价，表示强烈看涨', 1, 1, 0.6, 1),
        ('向下跳空', 'gap_down', '缺口形态', 'sell', '开盘价低于前一日最低价，表示强烈看跌', 1, 1, 0.6, 1),
        ('突破缺口', 'breakaway_gap', '缺口形态', 'neutral',
         '突破重要阻力或支撑时形成的缺口', 1, 5, 0.7, 1),
        ('中继缺口', 'runaway_gap', '缺口形态', 'neutral',
         '趋势中段出现的缺口，确认趋势继续', 1, 3, 0.6, 1),
        ('衰竭缺口', 'exhaustion_gap', '缺口形态', 'neutral',
         '趋势末端的缺口，预示趋势可能反转', 1, 3, 0.7, 1),
        ('普通缺口', 'common_gap', '缺口形态', 'neutral', '整理过程中的小缺口，通常会被回补', 1, 1, 0.3, 1),

        # 量价形态
        ('价涨量增', 'price_up_volume_up', '量价形态',
         'buy', '价格上涨伴随成交量放大，健康的上涨', 1, 5, 0.6, 1),
        ('价跌量增', 'price_down_volume_up', '量价形态',
         'sell', '价格下跌伴随成交量放大，空头力量强', 1, 5, 0.6, 1),
        ('价涨量缩', 'price_up_volume_down', '量价形态',
         'neutral', '价格上涨但成交量萎缩，上涨动力不足', 1, 5, 0.4, 1),
        ('价跌量缩', 'price_down_volume_down', '量价形态',
         'neutral', '价格下跌但成交量萎缩，抛压减轻', 1, 5, 0.4, 1),
        ('地量地价', 'low_volume_low_price', '量价形态',
         'buy', '成交量和价格都处于低位，可能是底部信号', 3, 10, 0.5, 1),
        ('天量天价', 'high_volume_high_price', '量价形态',
         'sell', '成交量和价格都处于高位，可能是顶部信号', 3, 10, 0.5, 1),
    ]

    cursor.executemany(
        '''INSERT OR IGNORE INTO pattern_types 
           (name, english_name, category, signal_type, description, min_periods, max_periods, confidence_threshold, is_active) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        patterns_data
    )

    # 20. 趋势预警配置表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trend_alert_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT DEFAULT 'default',
        config_name TEXT DEFAULT 'default',
        enable_price_alerts INTEGER DEFAULT 1,
        enable_trend_alerts INTEGER DEFAULT 1,
        enable_volume_alerts INTEGER DEFAULT 0,
        enable_technical_alerts INTEGER DEFAULT 1,
        price_change_threshold REAL DEFAULT 5.0,
        volume_change_threshold REAL DEFAULT 50.0,
        trend_strength_threshold REAL DEFAULT 0.7,
        alert_frequency TEXT DEFAULT 'immediate',
        notification_methods TEXT DEFAULT 'popup',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, config_name)
    )''')

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print('数据库初始化完成')
