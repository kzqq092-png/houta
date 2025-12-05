from loguru import logger
"""
api_server.py
RESTful API主服务

用法示例：
    # 启动API服务
    python api_server.py
    # 获取股票列表
    curl http://localhost:8000/api/stock/list
    # 回测
    curl -X POST http://localhost:8000/api/backtest -H "Content-Type: application/json" -d '{"code": "sh600000", "strategy": "MA"}'
    # 获取板块资金流排行榜
    curl http://localhost:8000/api/sector/fund-flow/ranking?date_range=today&sort_by=main_net_inflow
    # 获取板块历史趋势
    curl http://localhost:8000/api/sector/fund-flow/trend/BK0001?period=30
    # 获取板块分时资金流
    curl http://localhost:8000/api/sector/fund-flow/intraday/BK0001?date=2024-01-01
"""
from fastapi import FastAPI, Query, HTTPException
from typing import List, Dict, Any, Optional
import uvicorn
from ai_stock_selector import AIStockSelector
import pandas as pd
from datetime import datetime
from core.services.unified_data_manager import UnifiedDataManager
from utils.data_preprocessing import kdata_preprocess as _kdata_preprocess

# 假设有全局data_manager实例
from core.services.unified_data_manager import get_unified_data_manager
data_manager = get_unified_data_manager()

app = FastAPI(title="FactorWeave-Quant量化交易API", version="1.0.0")


@app.get("/")
def read_root():
    return {"message": "FactorWeave-Quant量化交易API服务"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "FactorWeave-Quant UI API"}


@app.get("/api/stock/list", response_model=List[Dict[str, Any]])
def get_stock_list():
    """
    获取股票列表
    返回：
        List[Dict]，每个dict包含code、name、market等字段
    """
    df = data_manager.get_stock_list()
    if df is not None and not df.empty:
        return df.to_dict(orient="records")
    return []


@app.post("/api/backtest")
def run_backtest(params: Dict[str, Any]):
    """
    执行回测
    参数：
        params: 包含code、strategy、参数等
    返回：
        dict，包含回测结果和性能指标
    """
    # TODO: 调用回测引擎
    return {"result": "success", "metrics": {}}


@app.post("/api/analyze")
def run_analysis(params: Dict[str, Any]):
    """
    执行分析
    参数：
        params: 分析参数
    返回：
        dict，包含分析结果
    """
    # TODO: 调用分析引擎
    return {"result": "success", "analysis": {}}


@app.post("/api/ai/select_stocks")
def ai_select_stocks(params: Dict[str, Any]):
    """
    AI智能选股API
    参数：
        params: {
            'stock_data': List[Dict],  # 股票特征数据（DataFrame转dict）
            'criteria': Dict,          # 选股条件
            'model_type': str          # 选股模型类型，可选
        }
    返回：
        dict: {'selected': [股票代码], 'explanations': {代码: 理由}}
    """
    stock_data = params.get('stock_data', [])
    criteria = params.get('criteria', {})
    model_type = params.get('model_type', 'ml')
    if not stock_data:
        return {"selected": [], "explanations": {}}
    df = pd.DataFrame(stock_data)
    df = _kdata_preprocess(df, context="API选股")
    if df is None or df.empty:
        return {"selected": [], "explanations": {}, "error": "数据全部无效或缺失关键字段"}
    selector = AIStockSelector(model_type=model_type)
    selected = selector.select_stocks(df, criteria)
    explanations = {code: selector.explain_selection(
        code) for code in selected}
    return {"selected": selected, "explanations": explanations}


@app.post("/api/ai/recommend_strategy")
def ai_recommend_strategy(params: Dict[str, Any]):
    """
    AI策略推荐API
    参数：
        params: {
            'stock_data': List[Dict],  # 股票特征数据
            'history': List[Dict],     # 历史表现（可选）
            'candidate_strategies': List[str]  # 候选策略列表（可选）
        }
    返回：
        dict: {'recommended': 策略名, 'reason': 推荐理由}
    """
    # TODO: 实现AI策略推荐逻辑（可用历史表现、特征、模型等）
    # 这里简单返回第一个候选策略和理由
    strategies = params.get('candidate_strategies', ['MA', 'MACD', 'RSI'])
    recommended = strategies[0] if strategies else 'MA'
    reason = "基于历史表现和特征，推荐最优策略。"
    return {"recommended": recommended, "reason": reason}


@app.post("/api/ai/optimize_params")
def ai_optimize_params(params: Dict[str, Any]):
    """
    AI参数优化API
    参数：
        params: {
            'strategy': str,           # 策略名
            'param_space': Dict,       # 参数空间（如{'fast': [5,10,20], 'slow': [20,50,100]}）
            'history': List[Dict]      # 历史数据
        }
    返回：
        dict: {'best_params': 最优参数, 'history': 优化过程}
    """
    # TODO: 实现AI参数优化逻辑（如网格搜索、贝叶斯优化等）
    # 这里简单返回第一个参数组合
    param_space = params.get(
        'param_space', {'fast': [5, 10], 'slow': [20, 50]})
    best_params = {k: v[0]
                   for k, v in param_space.items() if isinstance(v, list) and v}
    return {"best_params": best_params, "history": [best_params]}


@app.post("/api/ai/diagnosis")
def ai_diagnosis(params: Dict[str, Any]):
    """
    AI智能诊断API
    参数：
        params: {
            'result': Dict,    # 策略回测/分析结果
            'context': Dict    # 其他上下文信息（可选）
        }
    返回：
        dict: {'diagnosis': 诊断结论, 'suggestion': 改进建议}
    """
    # TODO: 实现AI诊断逻辑（如异常检测、因果分析、自动建议等）
    diagnosis = "策略表现正常，无明显异常。"
    suggestion = "可尝试调整参数或更换策略以提升收益。"
    return {"diagnosis": diagnosis, "suggestion": suggestion}

# ===========================================
# 板块资金流数据API
# ===========================================


@app.get("/api/sector/fund-flow/ranking")
def get_sector_fund_flow_ranking(
    date_range: str = Query(default="today", description="日期范围：today, 3d, 7d, 30d等"),
    sort_by: str = Query(default="main_net_inflow", description="排序字段：main_net_inflow, super_large_inflow等")
):
    """
    获取板块资金流排行榜

    参数：
        date_range: 日期范围，支持 today, 3d, 7d, 30d 等格式
        sort_by: 排序字段，如 main_net_inflow, super_large_inflow 等

    返回：
        List[Dict]: 板块资金流排行榜数据

    示例：
        GET /api/sector/fund-flow/ranking?date_range=today&sort_by=main_net_inflow
    """
    try:
        # 通过UnifiedDataManager获取板块数据服务
        sector_service = data_manager.get_sector_fund_flow_service()
        if sector_service is None:
            raise HTTPException(status_code=503, detail="板块数据服务不可用")

        # 获取排行榜数据
        df = sector_service.get_sector_fund_flow_ranking(date_range=date_range, sort_by=sort_by)

        if df is not None and not df.empty:
            # 转换为API响应格式
            result = df.to_dict(orient="records")
            return {
                "status": "success",
                "data": result,
                "count": len(result),
                "params": {"date_range": date_range, "sort_by": sort_by}
            }
        else:
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": "暂无数据"
            }

    except Exception as e:
        logger.error(f"获取板块资金流排行榜失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取板块资金流排行榜失败: {str(e)}")


@app.get("/api/sector/fund-flow/trend/{sector_id}")
def get_sector_historical_trend(
    sector_id: str,
    period: int = Query(default=30, description="历史天数，默认30天")
):
    """
    获取单板块历史趋势数据

    参数：
        sector_id: 板块ID，如 BK0001
        period: 历史天数，默认30天

    返回：
        List[Dict]: 板块历史趋势数据

    示例：
        GET /api/sector/fund-flow/trend/BK0001?period=30
    """
    try:
        # 通过UnifiedDataManager获取板块数据服务
        sector_service = data_manager.get_sector_fund_flow_service()
        if sector_service is None:
            raise HTTPException(status_code=503, detail="板块数据服务不可用")

        # 获取历史趋势数据
        df = sector_service.get_sector_historical_trend(sector_id=sector_id, period=period)

        if df is not None and not df.empty:
            # 转换为API响应格式
            result = df.to_dict(orient="records")
            return {
                "status": "success",
                "data": result,
                "count": len(result),
                "params": {"sector_id": sector_id, "period": period}
            }
        else:
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": f"板块 {sector_id} 暂无 {period} 天历史数据"
            }

    except Exception as e:
        logger.error(f"获取板块历史趋势失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取板块历史趋势失败: {str(e)}")


@app.get("/api/sector/fund-flow/intraday/{sector_id}")
def get_sector_intraday_flow(
    sector_id: str,
    date: str = Query(default=None, description="查询日期，格式YYYY-MM-DD，默认今日")
):
    """
    获取板块分时资金流数据

    参数：
        sector_id: 板块ID，如 BK0001
        date: 查询日期，格式 YYYY-MM-DD，默认今日

    返回：
        List[Dict]: 板块分时资金流数据

    示例：
        GET /api/sector/fund-flow/intraday/BK0001?date=2024-01-01
    """
    try:
        # 如果没有指定日期，使用今日
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # 验证日期格式
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")

        # 通过UnifiedDataManager获取板块数据服务
        sector_service = data_manager.get_sector_fund_flow_service()
        if sector_service is None:
            raise HTTPException(status_code=503, detail="板块数据服务不可用")

        # 获取分时资金流数据
        df = sector_service.get_sector_intraday_flow(sector_id=sector_id, date=date)

        if df is not None and not df.empty:
            # 转换为API响应格式
            result = df.to_dict(orient="records")
            return {
                "status": "success",
                "data": result,
                "count": len(result),
                "params": {"sector_id": sector_id, "date": date}
            }
        else:
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": f"板块 {sector_id} 在 {date} 暂无分时数据"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取板块分时资金流失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取板块分时资金流失败: {str(e)}")


@app.post("/api/sector/fund-flow/import")
def import_sector_historical_data(params: Dict[str, Any]):
    """
    导入板块历史数据

    参数：
        params: {
            'source': str,      # 数据源名称，如 'akshare', 'eastmoney'
            'start_date': str,  # 开始日期 YYYY-MM-DD
            'end_date': str,    # 结束日期 YYYY-MM-DD
        }

    返回：
        dict: 导入结果，包含成功状态和处理数量

    示例：
        POST /api/sector/fund-flow/import
        {
            "source": "akshare",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
    """
    try:
        # 验证必要参数
        source = params.get('source')
        start_date = params.get('start_date')
        end_date = params.get('end_date')

        if not all([source, start_date, end_date]):
            raise HTTPException(status_code=400, detail="缺少必要参数：source, start_date, end_date")

        # 验证日期格式
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")

        # 通过UnifiedDataManager获取板块数据服务
        sector_service = data_manager.get_sector_fund_flow_service()
        if sector_service is None:
            raise HTTPException(status_code=503, detail="板块数据服务不可用")

        # 执行历史数据导入
        import_result = sector_service.import_sector_historical_data(
            source=source,
            start_date=start_date,
            end_date=end_date
        )

        if import_result.get('success', False):
            return {
                "status": "success",
                "message": import_result.get('message', '导入成功'),
                "processed_count": import_result.get('processed_count', 0),
                "params": params
            }
        else:
            return {
                "status": "error",
                "message": import_result.get('error', '导入失败'),
                "processed_count": import_result.get('processed_count', 0),
                "params": params
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入板块历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入板块历史数据失败: {str(e)}")


@app.get("/api/sector/fund-flow/status")
def get_sector_service_status():
    """
    获取板块资金流服务状态

    返回：
        dict: 服务状态信息，包括可用性、数据源等

    示例：
        GET /api/sector/fund-flow/status
    """
    try:
        # 通过UnifiedDataManager获取板块数据服务
        sector_service = data_manager.get_sector_fund_flow_service()

        if sector_service is None:
            return {
                "status": "unavailable",
                "message": "板块数据服务不可用",
                "data_sources": []
            }

        # 获取服务状态（如果SectorDataService有状态方法的话）
        status_info = {
            "status": "available",
            "message": "板块数据服务运行正常",
            "service_type": "SectorDataService",
            "timestamp": datetime.now().isoformat()
        }

        # 如果有其他状态信息，可以在这里添加
        # 例如：可用数据源、缓存状态等

        return status_info

    except Exception as e:
        logger.error(f"获取板块服务状态失败: {e}")
        return {
            "status": "error",
            "message": f"获取服务状态失败: {str(e)}",
            "data_sources": []
        }

# 后续可扩展：用户认证、插件注册、WebHook等


def _kdata_preprocess(df, context="分析"):
    """K线数据预处理：检查并修正所有关键字段，统一处理datetime字段"""

    if not isinstance(df, pd.DataFrame):
        return df

    # 检查datetime是否在索引中或列中
    has_datetime = False
    datetime_in_index = False

    # 检查datetime是否在索引中
    if isinstance(df.index, pd.DatetimeIndex) or (hasattr(df.index, 'name') and df.index.name == 'datetime'):
        has_datetime = True
        datetime_in_index = True
    # 检查datetime是否在列中
    elif 'datetime' in df.columns:
        has_datetime = True
        datetime_in_index = False

    # 如果datetime不存在，尝试从索引推断或创建
    if not has_datetime:
        if isinstance(df.index, pd.DatetimeIndex):
            # 索引是DatetimeIndex但名称不是datetime，复制到列中
            df = df.copy()
            df['datetime'] = df.index
            has_datetime = True
            logger.info(f"[{context}] 从DatetimeIndex推断datetime字段")
        else:
            # 完全没有datetime信息，需要补全
            logger.info(f"[{context}] 缺少datetime字段，自动补全")
            df = df.copy()
            df['datetime'] = pd.date_range(
                start='2023-01-01', periods=len(df), freq='D')
            has_datetime = True

    # 检查其他必要字段
    required_cols = ['code', 'open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.info(f"[{context}] 缺少字段: {missing_cols}，自动补全为默认值")
        df = df.copy()
        for col in missing_cols:
            if col == 'code':
                df['code'] = ''
            elif col == 'volume':
                df[col] = 0.0
            elif col in ['open', 'high', 'low', 'close']:
                # 用收盘价填充其他价格字段
                if 'close' in df.columns:
                    df[col] = df['close']
                else:
                    df[col] = 0.0
            else:
                df[col] = 0.0

    # 检查数值字段异常
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            before = len(df)
            df = df[df[col].notna() & (df[col] >= 0)]
            after = len(df)
            if after < before:
                logger.info(f"[{context}] 已过滤{before-after}行{col}异常数据")

    # 检查code字段
    if 'code' in df.columns:
        df = df[df['code'].notna() & (df['code'] != '')]

    if df.empty:
        logger.info(f"[{context}] 数据全部无效，返回空")

    return df.reset_index(drop=True)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
