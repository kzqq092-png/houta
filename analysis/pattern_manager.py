"""
形态管理器模块
负责管理K线形态的配置和识别
"""

import sqlite3
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from analysis.pattern_recognition import PatternRecognizer


@dataclass
class PatternConfig:
    """形态配置数据类"""
    id: int
    name: str
    english_name: str
    category: str
    signal_type: str
    description: str
    min_periods: int
    max_periods: int
    confidence_threshold: float
    is_active: bool


class PatternManager:
    """形态管理器"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化形态管理器

        Args:
            db_path: 数据库路径，默认使用项目数据库
        """
        if db_path is None:
            self.db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'hikyuu_system.db')
        else:
            self.db_path = db_path

        self.pattern_recognizer = PatternRecognizer()
        self._patterns_cache = None

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
            patterns.append(PatternConfig(
                id=row[0], name=row[1], english_name=row[2],
                category=row[3], signal_type=row[4], description=row[5],
                min_periods=row[6], max_periods=row[7],
                confidence_threshold=row[8], is_active=bool(row[9])
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM pattern_types WHERE name = ? OR english_name = ?",
            (name, name)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return PatternConfig(
                id=row[0], name=row[1], english_name=row[2],
                category=row[3], signal_type=row[4], description=row[5],
                min_periods=row[6], max_periods=row[7],
                confidence_threshold=row[8], is_active=bool(row[9])
            )
        return None

    def get_categories(self) -> List[str]:
        """获取所有形态类别"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT category FROM pattern_types WHERE is_active = 1 ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()

        return categories

    def get_signal_types(self) -> List[str]:
        """获取所有信号类型"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT signal_type FROM pattern_types WHERE is_active = 1 ORDER BY signal_type")
        signal_types = [row[0] for row in cursor.fetchall()]
        conn.close()

        return signal_types

    def identify_all_patterns(self, kdata, selected_patterns: Optional[List[str]] = None,
                              confidence_threshold: float = 0.5) -> List[Dict]:
        """
        识别所有配置的形态，支持DataFrame和KData两种数据格式

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
        import pandas as pd
        original_data = kdata

        # 如果是DataFrame，确保包含必要字段
        if isinstance(kdata, pd.DataFrame):
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in kdata.columns]
            if missing_columns:
                print(f"DataFrame缺少必要列: {missing_columns}")
                return []

            # 增强的datetime处理逻辑
            if 'datetime' not in kdata.columns:
                if isinstance(kdata.index, pd.DatetimeIndex):
                    kdata = kdata.copy()
                    kdata['datetime'] = kdata.index
                    print("[PatternManager] 使用DatetimeIndex作为datetime字段")
                elif hasattr(kdata.index, 'name') and kdata.index.name == 'datetime':
                    # 如果index的名称是datetime，尝试转换
                    try:
                        kdata = kdata.copy()
                        kdata['datetime'] = pd.to_datetime(kdata.index)
                        print("[PatternManager] 从index名称推断datetime字段")
                    except Exception as e:
                        print(f"[PatternManager] 从index转换datetime失败: {e}")
                        # 使用序列号生成datetime
                        kdata = kdata.copy()
                        kdata['datetime'] = pd.date_range(start='2023-01-01', periods=len(kdata), freq='D')
                        print(f"[PatternManager] 自动生成datetime序列，长度: {len(kdata)}")
                else:
                    # 如果没有datetime信息，生成序列
                    print("[PatternManager] K线数据缺少datetime字段，自动补全为当前时间")
                    kdata = kdata.copy()
                    kdata['datetime'] = pd.date_range(start='2023-01-01', periods=len(kdata), freq='D')
                    print(f"[PatternManager] 自动生成datetime序列，长度: {len(kdata)}")
            else:
                # 确保datetime列是正确的时间格式
                try:
                    kdata = kdata.copy()
                    kdata['datetime'] = pd.to_datetime(kdata['datetime'])
                    print(f"[PatternManager] 转换现有datetime列为时间格式")
                except Exception as e:
                    print(f"[PatternManager] 转换datetime列失败: {e}, 将生成新的时间序列")
                    kdata['datetime'] = pd.date_range(start='2023-01-01', periods=len(kdata), freq='D')

            # 自动补全code字段
            if 'code' not in kdata.columns:
                kdata = kdata.copy()
                kdata['code'] = '000001'  # 默认代码

        patterns = self.get_pattern_configs(active_only=True)
        if selected_patterns:
            patterns = [p for p in patterns if p.english_name in selected_patterns]

        all_results = []

        print(f"[PatternManager] 开始识别形态，数据长度: {len(kdata)}, 形态类型数: {len(patterns)}")

        # 处理不同类别的形态
        for pattern in patterns:
            try:
                results = self._identify_single_pattern(original_data, pattern, confidence_threshold)
                all_results.extend(results)
                print(f"[PatternManager] 形态 {pattern.name} 识别结果: {len(results)} 个")
            except Exception as e:
                print(f"识别形态 {pattern.name} 时出错: {e}")
                continue

        print(f"[PatternManager] 形态识别完成，总计: {len(all_results)} 个形态")
        return all_results

    def _identify_single_pattern(self, kdata, pattern_config: PatternConfig,
                                 confidence_threshold: float) -> List[Dict]:
        """
        识别单个形态类型

        Args:
            kdata: K线数据
            pattern_config: 形态配置
            confidence_threshold: 置信度阈值

        Returns:
            识别结果列表
        """
        english_name = pattern_config.english_name

        # 根据形态类型调用相应的识别方法
        if english_name in ['double_top', 'double_bottom']:
            results = self.pattern_recognizer.find_double_tops_bottoms(kdata)
            # 过滤特定类型
            if english_name == 'double_top':
                results = [r for r in results if r.get('type') == 'double_top']
            else:
                results = [r for r in results if r.get('type') == 'double_bottom']

        elif english_name in ['head_shoulders_top', 'head_shoulders_bottom']:
            results = self.pattern_recognizer.find_head_shoulders(kdata)
            if english_name == 'head_shoulders_top':
                results = [r for r in results if r.get('type') == 'head_shoulders_top']
            else:
                results = [r for r in results if r.get('type') == 'head_shoulders_bottom']

        elif english_name in ['ascending_triangle', 'descending_triangle', 'symmetrical_triangle']:
            results = self.pattern_recognizer.find_triangles(kdata)
            results = [r for r in results if r.get('type') == english_name]

        else:
            # 使用通用形态识别方法
            results = self.pattern_recognizer.get_pattern_signals(
                kdata, pattern_types=[english_name]
            )

        # 过滤置信度并添加形态信息
        filtered_results = []
        for result in results:
            if result.get('confidence', 0) >= confidence_threshold:
                # 添加形态配置信息
                result['pattern_name'] = pattern_config.name
                result['pattern_category'] = pattern_config.category
                result['pattern_description'] = pattern_config.description
                filtered_results.append(result)

        return filtered_results

    def update_pattern_config(self, pattern_id: int, **kwargs) -> bool:
        """
        更新形态配置

        Args:
            pattern_id: 形态ID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        if not kwargs:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 构建更新语句
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [pattern_id]

        try:
            cursor.execute(
                f"UPDATE pattern_types SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            success = cursor.rowcount > 0
        except Exception as e:
            print(f"更新形态配置失败: {e}")
            success = False
        finally:
            conn.close()

        return success

    def add_pattern_config(self, name: str, english_name: str, category: str,
                           signal_type: str, description: str, **kwargs) -> Optional[int]:
        """
        添加新的形态配置

        Args:
            name: 形态名称
            english_name: 英文名称
            category: 类别
            signal_type: 信号类型
            description: 描述
            **kwargs: 其他配置参数

        Returns:
            新添加的形态ID，失败返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 设置默认值
        defaults = {
            'min_periods': 5,
            'max_periods': 60,
            'confidence_threshold': 0.5,
            'is_active': 1
        }
        defaults.update(kwargs)

        try:
            cursor.execute(
                """INSERT INTO pattern_types 
                   (name, english_name, category, signal_type, description, 
                    min_periods, max_periods, confidence_threshold, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, english_name, category, signal_type, description,
                 defaults['min_periods'], defaults['max_periods'],
                 defaults['confidence_threshold'], defaults['is_active'])
            )
            conn.commit()
            pattern_id = cursor.lastrowid
        except Exception as e:
            print(f"添加形态配置失败: {e}")
            pattern_id = None
        finally:
            conn.close()

        return pattern_id

    def get_pattern_statistics(self, kdata, pattern_name: str = None) -> Dict:
        """
        获取形态识别统计信息

        Args:
            kdata: K线数据
            pattern_name: 特定形态名称，None表示全部

        Returns:
            统计信息字典
        """
        patterns = self.identify_all_patterns(kdata)

        if pattern_name:
            patterns = [p for p in patterns if p.get('pattern_name') == pattern_name]

        stats = {
            'total_patterns': len(patterns),
            'by_category': {},
            'by_signal': {},
            'confidence_distribution': {
                'high': 0,  # >= 0.8
                'medium': 0,  # 0.5-0.8
                'low': 0  # < 0.5
            }
        }

        for pattern in patterns:
            # 按类别统计
            category = pattern.get('pattern_category', 'unknown')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

            # 按信号统计
            signal = pattern.get('signal', 'unknown')
            stats['by_signal'][signal] = stats['by_signal'].get(signal, 0) + 1

            # 置信度分布
            confidence = pattern.get('confidence', 0)
            if confidence >= 0.8:
                stats['confidence_distribution']['high'] += 1
            elif confidence >= 0.5:
                stats['confidence_distribution']['medium'] += 1
            else:
                stats['confidence_distribution']['low'] += 1

        return stats
