"""
指标组合管理器

用于管理用户的指标组合，包括保存、加载、删除和管理功能。
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IndicatorCombination:
    """指标组合数据类"""
    name: str
    description: str
    indicators: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndicatorCombination':
        """从字典创建实例"""
        return cls(**data)


class IndicatorCombinationManager:
    """指标组合管理器"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化指标组合管理器
        
        Args:
            data_dir: 数据存储目录，默认为 config/indicator_combinations
        """
        if data_dir is None:
            data_dir = os.path.join(os.getcwd(), 'config', 'indicator_combinations')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 组合文件路径
        self.combinations_file = self.data_dir / 'combinations.json'
        
        # 加载现有组合
        self.combinations = self._load_combinations()
        
        logger.info(f"Indicator combination manager initialized with {len(self.combinations)} combinations")
    
    def _load_combinations(self) -> Dict[str, IndicatorCombination]:
        """加载指标组合"""
        combinations = {}
        
        if self.combinations_file.exists():
            try:
                with open(self.combinations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for name, combination_data in data.items():
                    combinations[name] = IndicatorCombination.from_dict(combination_data)
                
                logger.debug(f"Loaded {len(combinations)} indicator combinations")
                
            except Exception as e:
                logger.error(f"Failed to load indicator combinations: {e}")
        
        return combinations
    
    def _save_combinations(self) -> bool:
        """保存指标组合"""
        try:
            data = {}
            for name, combination in self.combinations.items():
                data[name] = combination.to_dict()
            
            with open(self.combinations_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self.combinations)} indicator combinations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save indicator combinations: {e}")
            return False
    
    def save_combination(self, name: str, indicators: List[Dict[str, Any]], 
                        description: str = "", tags: List[str] = None) -> bool:
        """
        保存指标组合
        
        Args:
            name: 组合名称
            indicators: 指标列表
            description: 组合描述
            tags: 标签列表
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if not name or not indicators:
                logger.warning("Invalid combination name or indicators")
                return False
            
            # 检查是否已存在
            is_update = name in self.combinations
            
            # 创建时间戳
            now = datetime.now().isoformat()
            
            if is_update:
                # 更新现有组合
                combination = self.combinations[name]
                combination.indicators = indicators
                combination.description = description
                combination.updated_at = now
                if tags:
                    combination.tags = tags
            else:
                # 创建新组合
                combination = IndicatorCombination(
                    name=name,
                    description=description,
                    indicators=indicators,
                    created_at=now,
                    updated_at=now,
                    tags=tags or []
                )
            
            self.combinations[name] = combination
            
            # 保存到文件
            if self._save_combinations():
                action = "updated" if is_update else "created"
                logger.info(f"Indicator combination '{name}' {action} successfully")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to save combination '{name}': {e}")
            return False
    
    def load_combination(self, name: str) -> Optional[IndicatorCombination]:
        """
        加载指标组合
        
        Args:
            name: 组合名称
            
        Returns:
            IndicatorCombination: 指标组合，如果不存在则返回None
        """
        try:
            if name in self.combinations:
                combination = self.combinations[name]
                logger.debug(f"Loaded combination '{name}' with {len(combination.indicators)} indicators")
                return combination
            else:
                logger.warning(f"Combination '{name}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load combination '{name}': {e}")
            return None
    
    def delete_combination(self, name: str) -> bool:
        """
        删除指标组合
        
        Args:
            name: 组合名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if name in self.combinations:
                del self.combinations[name]
                
                # 保存到文件
                if self._save_combinations():
                    logger.info(f"Indicator combination '{name}' deleted successfully")
                    return True
                else:
                    return False
            else:
                logger.warning(f"Combination '{name}' not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete combination '{name}': {e}")
            return False
    
    def get_all_combinations(self) -> Dict[str, IndicatorCombination]:
        """
        获取所有指标组合
        
        Returns:
            Dict[str, IndicatorCombination]: 所有指标组合
        """
        return self.combinations.copy()
    
    def get_combination_names(self) -> List[str]:
        """
        获取所有组合名称
        
        Returns:
            List[str]: 组合名称列表
        """
        return list(self.combinations.keys())
    
    def search_combinations(self, query: str = "", tags: List[str] = None) -> Dict[str, IndicatorCombination]:
        """
        搜索指标组合
        
        Args:
            query: 搜索查询字符串
            tags: 标签过滤
            
        Returns:
            Dict[str, IndicatorCombination]: 匹配的组合
        """
        results = {}
        
        for name, combination in self.combinations.items():
            # 名称匹配
            name_match = not query or query.lower() in name.lower()
            
            # 描述匹配
            desc_match = not query or query.lower() in combination.description.lower()
            
            # 标签匹配
            tag_match = not tags or any(tag in combination.tags for tag in tags)
            
            # 指标名称匹配
            indicator_match = False
            if query:
                for indicator in combination.indicators:
                    if query.lower() in indicator.get('name', '').lower():
                        indicator_match = True
                        break
            
            if (name_match or desc_match or indicator_match) and tag_match:
                results[name] = combination
        
        logger.debug(f"Found {len(results)} combinations matching query '{query}'")
        return results
    
    def get_combination_stats(self) -> Dict[str, Any]:
        """
        获取组合统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            'total_combinations': len(self.combinations),
            'total_indicators': 0,
            'most_used_indicators': {},
            'tags': set(),
            'creation_dates': []
        }
        
        for combination in self.combinations.values():
            stats['total_indicators'] += len(combination.indicators)
            stats['creation_dates'].append(combination.created_at)
            
            # 统计标签
            stats['tags'].update(combination.tags)
            
            # 统计指标使用频率
            for indicator in combination.indicators:
                indicator_name = indicator.get('name', '')
                if indicator_name:
                    stats['most_used_indicators'][indicator_name] = \
                        stats['most_used_indicators'].get(indicator_name, 0) + 1
        
        # 转换集合为列表
        stats['tags'] = list(stats['tags'])
        
        # 按使用频率排序指标
        stats['most_used_indicators'] = dict(
            sorted(stats['most_used_indicators'].items(), 
                  key=lambda x: x[1], reverse=True)
        )
        
        return stats
    
    def export_combinations(self, file_path: str) -> bool:
        """
        导出指标组合到文件
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            bool: 是否导出成功
        """
        try:
            data = {}
            for name, combination in self.combinations.items():
                data[name] = combination.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(self.combinations)} combinations to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export combinations: {e}")
            return False
    
    def import_combinations(self, file_path: str, overwrite: bool = False) -> bool:
        """
        从文件导入指标组合
        
        Args:
            file_path: 导入文件路径
            overwrite: 是否覆盖现有组合
            
        Returns:
            bool: 是否导入成功
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Import file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            skipped_count = 0
            
            for name, combination_data in data.items():
                if name in self.combinations and not overwrite:
                    skipped_count += 1
                    continue
                
                combination = IndicatorCombination.from_dict(combination_data)
                self.combinations[name] = combination
                imported_count += 1
            
            # 保存到文件
            if self._save_combinations():
                logger.info(f"Imported {imported_count} combinations, skipped {skipped_count}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to import combinations: {e}")
            return False
    
    def backup_combinations(self, backup_dir: str = None) -> bool:
        """
        备份指标组合
        
        Args:
            backup_dir: 备份目录
            
        Returns:
            bool: 是否备份成功
        """
        try:
            if backup_dir is None:
                backup_dir = self.data_dir / 'backups'
            
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_path / f'combinations_backup_{timestamp}.json'
            
            return self.export_combinations(str(backup_file))
            
        except Exception as e:
            logger.error(f"Failed to backup combinations: {e}")
            return False


# 全局实例
_combination_manager = None


def get_combination_manager() -> IndicatorCombinationManager:
    """获取指标组合管理器实例"""
    global _combination_manager
    if _combination_manager is None:
        _combination_manager = IndicatorCombinationManager()
    return _combination_manager


def main():
    """测试函数"""
    # 创建管理器
    manager = IndicatorCombinationManager()
    
    # 测试保存组合
    test_indicators = [
        {'name': 'MA', 'type': '均线', 'params': {'period': 20}},
        {'name': 'MACD', 'type': '趋势', 'params': {'fast': 12, 'slow': 26}},
        {'name': 'RSI', 'type': '震荡', 'params': {'period': 14}}
    ]
    
    success = manager.save_combination(
        name="经典组合",
        indicators=test_indicators,
        description="经典的技术分析指标组合",
        tags=["经典", "趋势", "震荡"]
    )
    
    print(f"保存组合: {'成功' if success else '失败'}")
    
    # 测试加载组合
    combination = manager.load_combination("经典组合")
    if combination:
        print(f"加载组合: {combination.name}")
        print(f"指标数量: {len(combination.indicators)}")
        print(f"标签: {combination.tags}")
    
    # 测试搜索
    results = manager.search_combinations("经典")
    print(f"搜索结果: {len(results)} 个组合")
    
    # 测试统计
    stats = manager.get_combination_stats()
    print(f"统计信息: {stats}")


if __name__ == '__main__':
    main()