"""
形态管理器模块
负责管理K线形态的配置和识别
"""

import sqlite3
import os
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from analysis.pattern_recognition import PatternRecognizer
from analysis.pattern_base import (
    BasePatternRecognizer, PatternConfig, PatternResult,
    PatternAlgorithmFactory, SignalType, PatternCategory
)


class PatternManager:
    """形态管理器 - 增强版，支持数据库算法和统一接口"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化形态管理器

        Args:
            db_path: 数据库路径，默认使用项目数据库
        """
        if db_path is None:
            self.db_path = os.path.join(os.path.dirname(
                __file__), '..', 'db', 'hikyuu_system.db')
        else:
            self.db_path = db_path

        self.pattern_recognizer = PatternRecognizer()
        self._patterns_cache = None
        self._ensure_database_schema()

    def _ensure_database_schema(self):
        """确保数据库表结构正确"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查并添加新字段
        try:
            cursor.execute(
                'ALTER TABLE pattern_types ADD COLUMN algorithm_code TEXT')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute(
                'ALTER TABLE pattern_types ADD COLUMN parameters TEXT')
        except sqlite3.OperationalError:
            pass

        # 创建形态历史表（用于效果统计）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                trigger_date TEXT NOT NULL,
                trigger_price REAL NOT NULL,
                result_date TEXT,
                result_price REAL,
                return_rate REAL,
                is_successful INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建通达信形态导入表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tdx_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                formula TEXT NOT NULL,
                description TEXT,
                category TEXT,
                signal_type TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def get_pattern_configs(self, category: Optional[str] = None,
                            signal_type: Optional[str] = None,
                            active_only: bool = True) -> List[PatternConfig]:
        """
        获取形态配置列表

        Args:
            category: 形态类别筛选
            signal_type: 信号类型筛选 
            active_only: 是否只返回激活的形态

        Returns:
            形态配置列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM pattern_types WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if signal_type:
            query += " AND signal_type = ?"
            params.append(signal_type)

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY category, name"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        patterns = []
        for row in rows:
            # 解析参数
            parameters = {}
            if len(row) > 13 and row[13]:  # parameters字段是第13个字段（索引13）
                try:
                    parameters = json.loads(row[13])
                except json.JSONDecodeError:
                    parameters = {}

            # 转换枚举类型
            try:
                category_enum = PatternCategory(row[3])
            except ValueError:
                category_enum = PatternCategory.COMPLEX

            try:
                signal_enum = SignalType(row[4])
            except ValueError:
                signal_enum = SignalType.NEUTRAL

            patterns.append(PatternConfig(
                id=row[0],
                name=row[1],
                english_name=row[2],
                category=category_enum,
                signal_type=signal_enum,
                description=row[5],
                min_periods=row[6],
                max_periods=row[7],
                confidence_threshold=row[8],
                # 修复：algorithm_code是第12个字段（索引12）
                algorithm_code=row[12] if len(row) > 12 else "",
                parameters=parameters,
                is_active=bool(row[9])
            ))

        return patterns

    def get_pattern_by_name(self, name: str) -> Optional[PatternConfig]:
        """
        根据名称获取形态配置

        Args:
            name: 形态名称（中文或英文）

        Returns:
            形态配置或None
        """
        configs = self.get_pattern_configs(active_only=False)
        for config in configs:
            if config.name == name or config.english_name == name:
                return config
        return None

    def get_categories(self) -> List[str]:
        """获取所有形态类别"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT DISTINCT category FROM pattern_types WHERE is_active = 1 ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()

        return categories

    def get_signal_types(self) -> List[str]:
        """获取所有信号类型"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT DISTINCT signal_type FROM pattern_types WHERE is_active = 1 ORDER BY signal_type")
        signal_types = [row[0] for row in cursor.fetchall()]
        conn.close()

        return signal_types

    def identify_all_patterns(self, kdata, selected_patterns: Optional[List[str]] = None,
                              confidence_threshold: float = 0.5) -> List[Dict]:
        """
        识别所有配置的形态，使用新的统一框架

        Args:
            kdata: K线数据（DataFrame或KData对象）
            selected_patterns: 要识别的形态列表（英文名），None表示全部
            confidence_threshold: 置信度阈值

        Returns:
            识别到的形态列表
        """
        if kdata is None or len(kdata) == 0:
            return []

        # 数据格式检查和预处理

        # 如果是DataFrame，确保包含必要字段
        if isinstance(kdata, pd.DataFrame):
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [
                col for col in required_columns if col not in kdata.columns]
            if missing_columns:
                print(f"DataFrame缺少必要列: {missing_columns}")
                return []

            # 增强的datetime处理逻辑
            if 'datetime' not in kdata.columns:
                if isinstance(kdata.index, pd.DatetimeIndex):
                    kdata = kdata.copy()
                    kdata['datetime'] = kdata.index
                    print("[PatternManager] 使用DatetimeIndex作为datetime字段")
                else:
                    # 如果没有datetime信息，生成序列
                    print("[PatternManager] K线数据缺少datetime字段，自动补全")
                    kdata = kdata.copy()
                    kdata['datetime'] = pd.date_range(
                        start='2023-01-01', periods=len(kdata), freq='D')
            else:
                # 确保datetime列是正确的时间格式
                try:
                    kdata['datetime'] = pd.to_datetime(kdata['datetime'])
                except Exception as e:
                    print(f"[PatternManager] datetime字段转换失败: {e}")
                    kdata['datetime'] = pd.date_range(
                        start='2023-01-01', periods=len(kdata), freq='D')
        else:
            # 如果是其他格式，尝试转换为DataFrame
            try:
                from core.data_manager import data_manager
                kdata = data_manager.kdata_to_df(kdata)
            except Exception as e:
                print(f"[PatternManager] 数据转换失败: {e}")
                return []

        # 获取要识别的形态配置
        all_configs = self.get_pattern_configs()
        if selected_patterns:
            configs = [
                c for c in all_configs if c.english_name in selected_patterns]
        else:
            configs = all_configs

        all_results = []

        # 使用新框架识别形态
        for config in configs:
            # 修复：只有当传入的阈值大于配置阈值时才跳过
            # 这样可以确保高质量的形态配置不会被低阈值请求忽略
            if confidence_threshold > config.confidence_threshold:
                # 如果请求的阈值比配置要求的还高，使用请求的阈值
                effective_threshold = confidence_threshold
            else:
                # 否则使用配置的阈值
                effective_threshold = config.confidence_threshold

            try:
                # 创建识别器实例
                recognizer = PatternAlgorithmFactory.create(config)

                # 执行识别
                results = recognizer.recognize(kdata)

                # 过滤置信度 - 使用有效阈值
                filtered_results = [
                    r for r in results
                    if r.confidence >= effective_threshold
                ]

                # 转换为字典格式
                for result in filtered_results:
                    all_results.append(result.to_dict())

            except Exception as e:
                print(f"[PatternManager] 形态识别失败 {config.english_name}: {e}")
                continue

        # 按置信度排序
        all_results.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return all_results

    def add_pattern_config(self, name: str, english_name: str, category: str,
                           signal_type: str, description: str,
                           algorithm_code: str = "", parameters: Dict = None,
                           **kwargs) -> Optional[int]:
        """
        添加新的形态配置

        Args:
            name: 中文名称
            english_name: 英文名称
            category: 形态类别
            signal_type: 信号类型
            description: 描述
            algorithm_code: 算法代码
            parameters: 参数字典
            **kwargs: 其他参数

        Returns:
            新增记录的ID，失败返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            min_periods = kwargs.get('min_periods', 5)
            max_periods = kwargs.get('max_periods', 60)
            confidence_threshold = kwargs.get('confidence_threshold', 0.5)
            is_active = kwargs.get('is_active', True)

            parameters_json = json.dumps(parameters or {})

            cursor.execute('''
                INSERT INTO pattern_types 
                (name, english_name, category, signal_type, description, 
                 min_periods, max_periods, confidence_threshold, is_active,
                 algorithm_code, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, english_name, category, signal_type, description,
                  min_periods, max_periods, confidence_threshold, is_active,
                  algorithm_code, parameters_json))

            pattern_id = cursor.lastrowid
            conn.commit()

            # 清除缓存
            self._patterns_cache = None

            return pattern_id

        except Exception as e:
            print(f"添加形态配置失败: {e}")
            return None
        finally:
            conn.close()

    def update_pattern_config(self, pattern_id: int, **kwargs) -> bool:
        """
        更新形态配置

        Args:
            pattern_id: 形态ID
            **kwargs: 要更新的字段

        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 构建更新语句
            update_fields = []
            values = []

            for field, value in kwargs.items():
                if field == 'parameters' and isinstance(value, dict):
                    value = json.dumps(value)
                update_fields.append(f"{field} = ?")
                values.append(value)

            if not update_fields:
                return False

            values.append(pattern_id)
            query = f"UPDATE pattern_types SET {', '.join(update_fields)} WHERE id = ?"

            cursor.execute(query, values)
            conn.commit()

            # 清除缓存
            self._patterns_cache = None

            return cursor.rowcount > 0

        except Exception as e:
            print(f"更新形态配置失败: {e}")
            return False
        finally:
            conn.close()

    def delete_pattern_config(self, pattern_id: int) -> bool:
        """
        删除形态配置

        Args:
            pattern_id: 形态ID

        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "DELETE FROM pattern_types WHERE id = ?", (pattern_id,))
            conn.commit()

            # 清除缓存
            self._patterns_cache = None

            return cursor.rowcount > 0

        except Exception as e:
            print(f"删除形态配置失败: {e}")
            return False
        finally:
            conn.close()

    def import_tdx_formula(self, name: str, formula: str) -> bool:
        """导入通达信公式

        Args:
            name: 形态名称
            formula: 通达信公式代码

        Returns:
            是否导入成功
        """
        try:
            # 转换通达信公式为Python代码
            python_code = self._convert_tdx_formula(formula)

            if not python_code:
                return False

            # 创建新的形态配置
            config = PatternConfig(
                id=0,  # 将由数据库自动分配
                name=name,
                english_name=name.lower().replace(' ', '_'),
                category=PatternCategory.COMPLEX,
                signal_type=SignalType.NEUTRAL,
                description=f"通达信导入的形态: {name}",
                min_periods=1,
                max_periods=100,
                confidence_threshold=0.5,
                algorithm_code=python_code,
                parameters={},
                is_active=True
            )

            # 保存到数据库
            return self._save_pattern_config(config)

        except Exception as e:
            print(f"导入通达信公式失败: {e}")
            return False

    def _save_pattern_config(self, config: PatternConfig) -> bool:
        """保存形态配置到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO pattern_types (
                    name, english_name, category, signal_type, description,
                    min_periods, max_periods, confidence_threshold,
                    algorithm_code, parameters, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.name,
                config.english_name,
                config.category.value,
                config.signal_type.value,
                config.description,
                config.min_periods,
                config.max_periods,
                config.confidence_threshold,
                config.algorithm_code,
                json.dumps(config.parameters),
                config.is_active
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"保存形态配置失败: {e}")
            return False

    def _convert_tdx_formula(self, formula: str) -> str:
        """
        转换通达信公式为Python代码

        Args:
            formula: 通达信公式

        Returns:
            Python算法代码
        """
        # 这是一个简化的转换器，实际应用中需要更复杂的解析
        # 通达信常用函数映射
        tdx_mappings = {
            'C': "k['close']",
            'O': "k['open']",
            'H': "k['high']",
            'L': "k['low']",
            'V': "k['volume']",
            'REF(': 'kdata.iloc[i-',
            'MA(': 'kdata.rolling(',
            'AND': 'and',
            'OR': 'or',
            'NOT': 'not',
        }

        # 基础转换
        python_code = formula
        for tdx_func, py_func in tdx_mappings.items():
            python_code = python_code.replace(tdx_func, py_func)

        # 生成完整的算法代码模板
        algorithm_template = f'''
# 通达信公式转换: {formula}
for i in range(len(kdata)):
    k = kdata.iloc[i]
    
    try:
        # 转换后的条件判断
        condition = {python_code}
        
        if condition:
            confidence = 0.6  # 默认置信度
            datetime_val = str(kdata.iloc[i]['datetime']) if 'datetime' in kdata.columns else None
            
            result = create_result(
                pattern_type='tdx_pattern',
                signal_type=SignalType.NEUTRAL,
                confidence=confidence,
                index=i,
                price=k['close'],
                datetime_val=datetime_val,
                extra_data={{'original_formula': '{formula}'}}
            )
            results.append(result)
    except Exception as e:
        # 忽略单个K线的计算错误
        continue
'''

        return algorithm_template

    def get_pattern_statistics(self, kdata, pattern_name: str = None) -> Dict:
        """
        获取形态统计信息

        Args:
            kdata: K线数据
            pattern_name: 特定形态名称，None表示所有形态

        Returns:
            统计信息字典
        """
        try:
            # 识别形态
            if pattern_name:
                patterns = self.identify_all_patterns(kdata, [pattern_name])
            else:
                patterns = self.identify_all_patterns(kdata)

            if not patterns:
                return {
                    'total_patterns': 0,
                    'by_category': {},
                    'by_signal': {},
                    'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
                }

            # 统计分析
            stats = {
                'total_patterns': len(patterns),
                'by_category': {},
                'by_signal': {},
                'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
            }

            for pattern in patterns:
                # 按类别统计
                category = pattern.get('pattern_category', '未分类')
                stats['by_category'][category] = stats['by_category'].get(
                    category, 0) + 1

                # 按信号统计
                signal = pattern.get('signal', 'neutral')
                signal_cn = {'buy': '买入', 'sell': '卖出',
                             'neutral': '中性'}.get(signal, signal)
                stats['by_signal'][signal_cn] = stats['by_signal'].get(
                    signal_cn, 0) + 1

                # 按置信度统计
                confidence = pattern.get('confidence', 0)
                if confidence >= 0.8:
                    stats['confidence_distribution']['high'] += 1
                elif confidence >= 0.5:
                    stats['confidence_distribution']['medium'] += 1
                else:
                    stats['confidence_distribution']['low'] += 1

            return stats

        except Exception as e:
            print(f"获取形态统计失败: {e}")
            return {
                'total_patterns': 0,
                'by_category': {},
                'by_signal': {},
                'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
            }

    def get_pattern_effectiveness(self, pattern_type: str, days: int = 30) -> Dict:
        """
        获取形态有效性统计

        Args:
            pattern_type: 形态类型
            days: 统计天数

        Returns:
            有效性统计
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_count,
                    AVG(return_rate) as avg_return,
                    COUNT(CASE WHEN is_successful = 1 THEN 1 END) as success_count,
                    AVG(confidence) as avg_confidence
                FROM pattern_history 
                WHERE pattern_type = ? 
                AND trigger_date >= date('now', '-{} days')
            '''.format(days), (pattern_type,))

            row = cursor.fetchone()
            if row and row[0] > 0:
                return {
                    'total_signals': row[0],
                    'success_rate': (row[2] / row[0]) * 100 if row[0] > 0 else 0,
                    'average_return': row[1] or 0,
                    'average_confidence': row[3] or 0
                }
            else:
                return {
                    'total_signals': 0,
                    'success_rate': 0,
                    'average_return': 0,
                    'average_confidence': 0
                }

        except Exception as e:
            print(f"获取形态有效性失败: {e}")
            return {
                'total_signals': 0,
                'success_rate': 0,
                'average_return': 0,
                'average_confidence': 0
            }
        finally:
            conn.close()

    def record_pattern_result(self, pattern_type: str, stock_code: str,
                              signal_type: str, confidence: float,
                              trigger_date: str, trigger_price: float,
                              result_date: str = None, result_price: float = None) -> bool:
        """
        记录形态识别结果（用于效果统计）

        Args:
            pattern_type: 形态类型
            stock_code: 股票代码
            signal_type: 信号类型
            confidence: 置信度
            trigger_date: 触发日期
            trigger_price: 触发价格
            result_date: 结果日期
            result_price: 结果价格

        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 计算收益率和成功标志
            return_rate = None
            is_successful = None

            if result_price is not None and trigger_price > 0:
                return_rate = (result_price - trigger_price) / \
                    trigger_price * 100

                # 根据信号类型判断是否成功
                if signal_type == 'buy':
                    is_successful = 1 if return_rate > 0 else 0
                elif signal_type == 'sell':
                    is_successful = 1 if return_rate < 0 else 0
                else:
                    is_successful = 1 if abs(
                        return_rate) < 2 else 0  # 中性信号，波动小于2%算成功

            cursor.execute('''
                INSERT INTO pattern_history 
                (pattern_type, stock_code, signal_type, confidence, 
                 trigger_date, trigger_price, result_date, result_price, 
                 return_rate, is_successful)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pattern_type, stock_code, signal_type, confidence,
                  trigger_date, trigger_price, result_date, result_price,
                  return_rate, is_successful))

            conn.commit()
            return True

        except Exception as e:
            print(f"记录形态结果失败: {e}")
            return False
        finally:
            conn.close()

    def get_recommended_patterns(self, top_n: int = 10) -> List[Dict]:
        """
        获取推荐形态（基于历史效果）

        Args:
            top_n: 返回前N个推荐形态

        Returns:
            推荐形态列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT 
                    pattern_type,
                    COUNT(*) as total_count,
                    AVG(return_rate) as avg_return,
                    COUNT(CASE WHEN is_successful = 1 THEN 1 END) * 1.0 / COUNT(*) as success_rate,
                    AVG(confidence) as avg_confidence
                FROM pattern_history 
                WHERE trigger_date >= date('now', '-90 days')
                GROUP BY pattern_type
                HAVING total_count >= 5
                ORDER BY success_rate DESC, avg_return DESC
                LIMIT ?
            ''', (top_n,))

            recommendations = []
            for row in cursor.fetchall():
                recommendations.append({
                    'pattern_type': row[0],
                    'total_signals': row[1],
                    'average_return': round(row[2] or 0, 2),
                    'success_rate': round(row[3] * 100, 2),
                    'average_confidence': round(row[4] or 0, 3),
                    'recommendation_score': round((row[3] * 0.6 + (row[2] or 0) * 0.004 + (row[4] or 0) * 0.4), 3)
                })

            return recommendations

        except Exception as e:
            print(f"获取推荐形态失败: {e}")
            return []
        finally:
            conn.close()

    def get_all_patterns(self, active_only: bool = True) -> List[PatternConfig]:
        """
        获取所有形态配置（兼容优化系统接口）

        Args:
            active_only: 是否只返回激活的形态

        Returns:
            形态配置列表
        """
        return self.get_pattern_configs(active_only=active_only)
