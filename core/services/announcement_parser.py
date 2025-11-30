"""
公告解析引擎

智能解析公司公告，提供自动分类、关键信息提取、重要性评级等功能。
支持多种公告类型的智能识别和结构化处理。

作者: FactorWeave-Quant增强团队
版本: 1.0
日期: 2025-09-21
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import pandas as pd

from loguru import logger

# 尝试导入jieba，如果失败则使用简单的分词替代
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    logger.warning("jieba模块不可用，将使用简单分词功能")
    JIEBA_AVAILABLE = False

    # 创建jieba的简单替代
    class SimpleJieba:
        @staticmethod
        def initialize():
            pass

        @staticmethod
        def cut(text):
            # 简单的中文分词替代：按标点符号和空格分割
            import re
            return re.findall(r'[\w\u4e00-\u9fff]+', text)

    jieba = SimpleJieba()

logger = logger.bind(module=__name__)


@dataclass
class ParsedAnnouncement:
    """解析后的公告数据"""
    original_title: str
    original_content: str

    # 分类结果
    category: str  # 主分类
    subcategory: str  # 子分类
    confidence_score: float  # 分类置信度

    # 关键信息提取
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    key_dates: List[datetime] = field(default_factory=list)
    key_amounts: List[float] = field(default_factory=list)
    key_percentages: List[float] = field(default_factory=list)

    # 情绪分析
    sentiment_score: float = 0.0  # -1到1
    sentiment_label: str = "中性"  # 正面/负面/中性

    # 重要性评级
    importance_level: int = 3  # 1-5级，5最重要
    impact_assessment: str = ""

    # 实体识别
    mentioned_companies: List[str] = field(default_factory=list)
    mentioned_products: List[str] = field(default_factory=list)
    mentioned_regions: List[str] = field(default_factory=list)

    # 元数据
    parse_time: datetime = field(default_factory=datetime.now)
    parser_version: str = "1.0"


class AnnouncementParser:
    """
    公告解析引擎

    提供智能公告分类、关键信息提取、重要性评级等功能。
    支持多种公告类型的自动识别和结构化处理。
    """

    def __init__(self):
        # 公告分类规则
        self.category_rules = {
            '业绩相关': {
                'keywords': ['业绩预告', '业绩快报', '年报', '季报', '半年报', '净利润', '营业收入', '盈利'],
                'patterns': [
                    r'净利润.*?(\d+\.?\d*)[万亿千百十]?元',
                    r'营业收入.*?(\d+\.?\d*)[万亿千百十]?元',
                    r'同比.*?增长.*?(\d+\.?\d*)%',
                    r'预计.*?净利润.*?(\d+\.?\d*)[万亿千百十]?元'
                ],
                'importance_base': 4
            },
            '重大事项': {
                'keywords': ['重大资产重组', '收购', '兼并', '投资', '合作协议', '战略合作', '重大合同'],
                'patterns': [
                    r'投资.*?(\d+\.?\d*)[万亿千百十]?元',
                    r'收购.*?(\d+\.?\d*)%.*?股权',
                    r'合同金额.*?(\d+\.?\d*)[万亿千百十]?元'
                ],
                'importance_base': 4
            },
            '股权变动': {
                'keywords': ['股权转让', '增持', '减持', '股东', '控股', '股份变动'],
                'patterns': [
                    r'增持.*?(\d+\.?\d*)[万千百十]?股',
                    r'减持.*?(\d+\.?\d*)[万千百十]?股',
                    r'持股比例.*?(\d+\.?\d*)%'
                ],
                'importance_base': 3
            },
            '分红派息': {
                'keywords': ['分红', '派息', '股息', '红利', '现金分红', '股票股利'],
                'patterns': [
                    r'每10股.*?派.*?(\d+\.?\d*)元',
                    r'股息率.*?(\d+\.?\d*)%',
                    r'分红.*?(\d+\.?\d*)[万亿千百十]?元'
                ],
                'importance_base': 2
            },
            '风险提示': {
                'keywords': ['风险提示', '诉讼', '仲裁', '处罚', '调查', '违规', '停牌'],
                'patterns': [
                    r'诉讼.*?金额.*?(\d+\.?\d*)[万亿千百十]?元',
                    r'罚款.*?(\d+\.?\d*)[万千百十]?元'
                ],
                'importance_base': 4
            },
            '人事变动': {
                'keywords': ['董事', '监事', '高管', '总经理', '董事长', '辞职', '任命'],
                'patterns': [
                    r'(董事长|总经理|副总经理|财务总监|董事会秘书).*?(辞职|任命|变更)'
                ],
                'importance_base': 2
            },
            '其他公告': {
                'keywords': ['澄清', '说明', '提示性公告', '补充公告'],
                'patterns': [],
                'importance_base': 1
            }
        }

        # 情绪词典
        self.positive_words = {
            '增长', '上升', '提高', '改善', '优化', '成功', '突破', '创新', '领先', '优秀',
            '盈利', '收益', '利润', '营收', '业绩', '发展', '扩张', '合作', '签约', '中标'
        }

        self.negative_words = {
            '下降', '减少', '亏损', '损失', '风险', '问题', '困难', '挑战', '诉讼', '处罚',
            '违规', '停牌', '延期', '取消', '终止', '失败', '下滑', '恶化', '减持', '辞职'
        }

        # 数值提取模式
        self.amount_patterns = [
            r'(\d+\.?\d*)[万亿千百十]?元',
            r'(\d+\.?\d*)[万亿千百十]?股',
            r'(\d+\.?\d*)%',
            r'(\d{4})[年]?(\d{1,2})[月]?(\d{1,2})?[日]?'
        ]

        # 初始化分词器
        jieba.initialize()

        logger.info("公告解析引擎初始化完成")

    def parse_announcement(self, title: str, content: str) -> ParsedAnnouncement:
        """
        解析公告

        Args:
            title: 公告标题
            content: 公告内容

        Returns:
            ParsedAnnouncement: 解析结果
        """
        try:
            logger.debug(f"开始解析公告: {title[:50]}...")

            # 1. 公告分类
            category, subcategory, confidence = self._classify_announcement(title, content)

            # 2. 关键信息提取
            key_metrics = self._extract_key_metrics(title, content, category)
            key_dates = self._extract_dates(content)
            key_amounts = self._extract_amounts(content)
            key_percentages = self._extract_percentages(content)

            # 3. 情绪分析
            sentiment_score, sentiment_label = self._analyze_sentiment(title, content)

            # 4. 重要性评级
            importance_level, impact_assessment = self._assess_importance(
                title, content, category, key_metrics
            )

            # 5. 实体识别
            mentioned_companies = self._extract_companies(content)
            mentioned_products = self._extract_products(content)
            mentioned_regions = self._extract_regions(content)

            # 构建解析结果
            parsed = ParsedAnnouncement(
                original_title=title,
                original_content=content,
                category=category,
                subcategory=subcategory,
                confidence_score=confidence,
                key_metrics=key_metrics,
                key_dates=key_dates,
                key_amounts=key_amounts,
                key_percentages=key_percentages,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                importance_level=importance_level,
                impact_assessment=impact_assessment,
                mentioned_companies=mentioned_companies,
                mentioned_products=mentioned_products,
                mentioned_regions=mentioned_regions
            )

            logger.info(f"公告解析完成: 分类={category}, 重要性={importance_level}, 情绪={sentiment_label}")
            return parsed

        except Exception as e:
            logger.error(f"公告解析失败: {e}")
            # 返回基础解析结果
            return ParsedAnnouncement(
                original_title=title,
                original_content=content,
                category="其他公告",
                subcategory="",
                confidence_score=0.5
            )

    def _classify_announcement(self, title: str, content: str) -> Tuple[str, str, float]:
        """公告分类"""
        try:
            text = title + " " + content
            text = text.lower()

            category_scores = {}

            # 基于关键词匹配计算分数
            for category, rules in self.category_rules.items():
                score = 0

                # 关键词匹配
                for keyword in rules['keywords']:
                    if keyword in text:
                        score += 1

                # 模式匹配
                for pattern in rules['patterns']:
                    matches = re.findall(pattern, text)
                    score += len(matches) * 2  # 模式匹配权重更高

                if score > 0:
                    category_scores[category] = score

            if not category_scores:
                return "其他公告", "", 0.5

            # 选择得分最高的分类
            best_category = max(category_scores, key=category_scores.get)
            max_score = category_scores[best_category]

            # 计算置信度
            total_score = sum(category_scores.values())
            confidence = max_score / total_score if total_score > 0 else 0.5

            # 子分类（简化处理）
            subcategory = self._get_subcategory(best_category, title, content)

            return best_category, subcategory, confidence

        except Exception as e:
            logger.error(f"公告分类失败: {e}")
            return "其他公告", "", 0.5

    def _get_subcategory(self, category: str, title: str, content: str) -> str:
        """获取子分类"""
        try:
            if category == "业绩相关":
                if "预告" in title:
                    return "业绩预告"
                elif "快报" in title:
                    return "业绩快报"
                elif "年报" in title:
                    return "年度报告"
                elif "季报" in title or "三季" in title:
                    return "季度报告"
                else:
                    return "业绩公告"

            elif category == "重大事项":
                if "收购" in title or "并购" in title:
                    return "收购兼并"
                elif "投资" in title:
                    return "对外投资"
                elif "合作" in title:
                    return "战略合作"
                else:
                    return "重大事项"

            elif category == "股权变动":
                if "增持" in title:
                    return "股东增持"
                elif "减持" in title:
                    return "股东减持"
                else:
                    return "股权变动"

            return ""

        except Exception as e:
            logger.error(f"获取子分类失败: {e}")
            return ""

    def _extract_key_metrics(self, title: str, content: str, category: str) -> Dict[str, Any]:
        """提取关键指标"""
        try:
            metrics = {}
            text = title + " " + content

            if category == "业绩相关":
                # 提取业绩相关指标

                # 净利润
                net_profit_pattern = r'净利润.*?(\d+\.?\d*)[万亿千百十]?元'
                matches = re.findall(net_profit_pattern, text)
                if matches:
                    metrics['净利润'] = self._convert_amount(matches[0])

                # 营业收入
                revenue_pattern = r'营业收入.*?(\d+\.?\d*)[万亿千百十]?元'
                matches = re.findall(revenue_pattern, text)
                if matches:
                    metrics['营业收入'] = self._convert_amount(matches[0])

                # 同比增长率
                growth_pattern = r'同比.*?增长.*?(\d+\.?\d*)%'
                matches = re.findall(growth_pattern, text)
                if matches:
                    metrics['同比增长率'] = float(matches[0])

            elif category == "重大事项":
                # 提取投资金额
                investment_pattern = r'投资.*?(\d+\.?\d*)[万亿千百十]?元'
                matches = re.findall(investment_pattern, text)
                if matches:
                    metrics['投资金额'] = self._convert_amount(matches[0])

                # 合同金额
                contract_pattern = r'合同金额.*?(\d+\.?\d*)[万亿千百十]?元'
                matches = re.findall(contract_pattern, text)
                if matches:
                    metrics['合同金额'] = self._convert_amount(matches[0])

            elif category == "股权变动":
                # 持股比例
                holding_pattern = r'持股比例.*?(\d+\.?\d*)%'
                matches = re.findall(holding_pattern, text)
                if matches:
                    metrics['持股比例'] = float(matches[0])

                # 变动股数
                shares_pattern = r'(增持|减持).*?(\d+\.?\d*)[万千百十]?股'
                matches = re.findall(shares_pattern, text)
                if matches:
                    action, amount = matches[0]
                    metrics['变动类型'] = action
                    metrics['变动股数'] = self._convert_amount(amount)

            elif category == "分红派息":
                # 分红方案
                dividend_pattern = r'每10股.*?派.*?(\d+\.?\d*)元'
                matches = re.findall(dividend_pattern, text)
                if matches:
                    metrics['每10股派息'] = float(matches[0])

                # 股息率
                yield_pattern = r'股息率.*?(\d+\.?\d*)%'
                matches = re.findall(yield_pattern, text)
                if matches:
                    metrics['股息率'] = float(matches[0])

            return metrics

        except Exception as e:
            logger.error(f"提取关键指标失败: {e}")
            return {}

    def _extract_dates(self, content: str) -> List[datetime]:
        """提取日期"""
        try:
            dates = []

            # 日期模式
            date_patterns = [
                r'(\d{4})年(\d{1,2})月(\d{1,2})日',
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{4})\.(\d{1,2})\.(\d{1,2})'
            ]

            for pattern in date_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    try:
                        year, month, day = map(int, match)
                        date = datetime(year, month, day)
                        if date not in dates:
                            dates.append(date)
                    except ValueError:
                        continue

            return sorted(dates)

        except Exception as e:
            logger.error(f"提取日期失败: {e}")
            return []

    def _extract_amounts(self, content: str) -> List[float]:
        """提取金额"""
        try:
            amounts = []

            # 金额模式
            amount_pattern = r'(\d+\.?\d*)[万亿千百十]?元'
            matches = re.findall(amount_pattern, content)

            for match in matches:
                amount = self._convert_amount(match)
                if amount > 0:
                    amounts.append(amount)

            return sorted(set(amounts), reverse=True)  # 去重并按金额降序排列

        except Exception as e:
            logger.error(f"提取金额失败: {e}")
            return []

    def _extract_percentages(self, content: str) -> List[float]:
        """提取百分比"""
        try:
            percentages = []

            # 百分比模式
            percentage_pattern = r'(\d+\.?\d*)%'
            matches = re.findall(percentage_pattern, content)

            for match in matches:
                try:
                    percentage = float(match)
                    if 0 <= percentage <= 100:  # 合理范围内的百分比
                        percentages.append(percentage)
                except ValueError:
                    continue

            return sorted(set(percentages), reverse=True)  # 去重并降序排列

        except Exception as e:
            logger.error(f"提取百分比失败: {e}")
            return []

    def _analyze_sentiment(self, title: str, content: str) -> Tuple[float, str]:
        """情绪分析"""
        try:
            text = title + " " + content
            words = list(jieba.cut(text))

            positive_count = sum(1 for word in words if word in self.positive_words)
            negative_count = sum(1 for word in words if word in self.negative_words)

            total_sentiment_words = positive_count + negative_count

            if total_sentiment_words == 0:
                return 0.0, "中性"

            # 计算情绪分数
            sentiment_score = (positive_count - negative_count) / total_sentiment_words

            # 确定情绪标签
            if sentiment_score > 0.2:
                sentiment_label = "正面"
            elif sentiment_score < -0.2:
                sentiment_label = "负面"
            else:
                sentiment_label = "中性"

            return sentiment_score, sentiment_label

        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            return 0.0, "中性"

    def _assess_importance(self, title: str, content: str, category: str,
                           key_metrics: Dict[str, Any]) -> Tuple[int, str]:
        """重要性评级"""
        try:
            # 基础重要性分数
            base_score = self.category_rules.get(category, {}).get('importance_base', 3)

            # 根据关键指标调整重要性
            adjustment = 0

            if category == "业绩相关":
                # 业绩变化幅度影响重要性
                if '同比增长率' in key_metrics:
                    growth_rate = abs(key_metrics['同比增长率'])
                    if growth_rate > 50:
                        adjustment += 1
                    elif growth_rate > 20:
                        adjustment += 0.5

                # 净利润规模影响重要性
                if '净利润' in key_metrics:
                    net_profit = key_metrics['净利润']
                    if net_profit > 1000000000:  # 10亿以上
                        adjustment += 1
                    elif net_profit > 100000000:  # 1亿以上
                        adjustment += 0.5

            elif category == "重大事项":
                # 投资金额影响重要性
                if '投资金额' in key_metrics:
                    investment = key_metrics['投资金额']
                    if investment > 1000000000:  # 10亿以上
                        adjustment += 1
                    elif investment > 100000000:  # 1亿以上
                        adjustment += 0.5

            elif category == "风险提示":
                # 风险类公告默认重要性较高
                adjustment += 1

            # 标题关键词影响重要性
            high_importance_keywords = ['重大', '紧急', '重要', '特别', '临时']
            for keyword in high_importance_keywords:
                if keyword in title:
                    adjustment += 0.5
                    break

            # 计算最终重要性等级
            final_score = base_score + adjustment
            importance_level = max(1, min(5, int(round(final_score))))

            # 生成影响评估
            impact_assessment = self._generate_impact_assessment(
                category, importance_level, key_metrics
            )

            return importance_level, impact_assessment

        except Exception as e:
            logger.error(f"重要性评级失败: {e}")
            return 3, "中等影响"

    def _generate_impact_assessment(self, category: str, importance_level: int,
                                    key_metrics: Dict[str, Any]) -> str:
        """生成影响评估"""
        try:
            if importance_level >= 4:
                impact_prefix = "重大影响"
            elif importance_level >= 3:
                impact_prefix = "中等影响"
            else:
                impact_prefix = "轻微影响"

            if category == "业绩相关":
                if '同比增长率' in key_metrics:
                    growth = key_metrics['同比增长率']
                    if growth > 0:
                        return f"{impact_prefix}：业绩增长{growth:.1f}%，对股价可能产生正面影响"
                    else:
                        return f"{impact_prefix}：业绩下滑{abs(growth):.1f}%，对股价可能产生负面影响"
                else:
                    return f"{impact_prefix}：业绩公告发布，需关注具体数据"

            elif category == "重大事项":
                if '投资金额' in key_metrics:
                    amount = key_metrics['投资金额']
                    return f"{impact_prefix}：重大投资{amount/100000000:.1f}亿元，影响公司未来发展"
                else:
                    return f"{impact_prefix}：重大事项公告，需关注具体内容"

            elif category == "股权变动":
                if '持股比例' in key_metrics:
                    ratio = key_metrics['持股比例']
                    return f"{impact_prefix}：股权变动至{ratio:.2f}%，可能影响公司治理结构"
                else:
                    return f"{impact_prefix}：股权结构发生变化"

            elif category == "风险提示":
                return f"{impact_prefix}：存在风险因素，投资者需谨慎关注"

            else:
                return f"{impact_prefix}：{category}类公告"

        except Exception as e:
            logger.error(f"生成影响评估失败: {e}")
            return "需要进一步分析"

    def _extract_companies(self, content: str) -> List[str]:
        """提取提及的公司"""
        try:
            companies = []

            # 公司名称模式
            company_patterns = [
                r'([A-Z]{2,}[a-z]*(?:\s+[A-Z][a-z]*)*(?:\s+(?:Inc|Corp|Ltd|Co|Group|Holdings)\.?))',
                r'([\u4e00-\u9fa5]+(?:股份)?(?:有限)?公司)',
                r'([\u4e00-\u9fa5]+集团)',
                r'([\u4e00-\u9fa5]+银行)',
                r'([\u4e00-\u9fa5]+保险)'
            ]

            for pattern in company_patterns:
                matches = re.findall(pattern, content)
                companies.extend(matches)

            # 去重并过滤
            companies = list(set(companies))
            companies = [c for c in companies if len(c) > 2 and len(c) < 50]

            return companies[:10]  # 最多返回10个

        except Exception as e:
            logger.error(f"提取公司名称失败: {e}")
            return []

    def _extract_products(self, content: str) -> List[str]:
        """提取提及的产品"""
        try:
            products = []

            # 产品关键词
            product_keywords = [
                '产品', '服务', '技术', '平台', '系统', '软件', '设备', '装置',
                '药品', '疫苗', '器械', '芯片', '电池', '材料', '化工', '钢铁'
            ]

            # 简单的产品提取（基于关键词前后的词汇）
            for keyword in product_keywords:
                pattern = f'([\\u4e00-\\u9fa5]{{2,8}}){keyword}'
                matches = re.findall(pattern, content)
                products.extend([m + keyword for m in matches])

            # 去重并过滤
            products = list(set(products))
            products = [p for p in products if len(p) > 2 and len(p) < 20]

            return products[:5]  # 最多返回5个

        except Exception as e:
            logger.error(f"提取产品名称失败: {e}")
            return []

    def _extract_regions(self, content: str) -> List[str]:
        """提取提及的地区"""
        try:
            regions = []

            # 地区模式
            region_patterns = [
                r'(北京|上海|广州|深圳|杭州|南京|苏州|成都|重庆|天津|武汉|西安|青岛|大连|厦门)',
                r'([\u4e00-\u9fa5]{2,4}省)',
                r'([\u4e00-\u9fa5]{2,4}市)',
                r'([\u4e00-\u9fa5]{2,4}区)',
                r'(美国|欧洲|日本|韩国|新加坡|香港|台湾|澳门)'
            ]

            for pattern in region_patterns:
                matches = re.findall(pattern, content)
                regions.extend(matches)

            # 去重
            regions = list(set(regions))

            return regions[:5]  # 最多返回5个

        except Exception as e:
            logger.error(f"提取地区名称失败: {e}")
            return []

    def _convert_amount(self, amount_str: str) -> float:
        """转换金额字符串为数值"""
        try:
            # 移除非数字字符（除了小数点）
            clean_str = re.sub(r'[^\d.]', '', amount_str)
            if not clean_str:
                return 0.0

            amount = float(clean_str)

            # 根据单位进行转换
            if '万' in amount_str:
                amount *= 10000
            elif '千万' in amount_str:
                amount *= 10000000
            elif '亿' in amount_str:
                amount *= 100000000
            elif '千亿' in amount_str:
                amount *= 100000000000
            elif '万亿' in amount_str:
                amount *= 1000000000000

            return amount

        except Exception as e:
            logger.error(f"转换金额失败: {amount_str}, {e}")
            return 0.0

    def batch_parse_announcements(self, announcements: List[Dict[str, str]]) -> List[ParsedAnnouncement]:
        """批量解析公告"""
        try:
            logger.info(f"开始批量解析公告: {len(announcements)}条")

            parsed_results = []

            for i, announcement in enumerate(announcements):
                try:
                    title = announcement.get('title', '')
                    content = announcement.get('content', '')

                    parsed = self.parse_announcement(title, content)
                    parsed_results.append(parsed)

                    if (i + 1) % 10 == 0:
                        logger.info(f"批量解析进度: {i + 1}/{len(announcements)}")

                except Exception as e:
                    logger.error(f"解析第{i+1}条公告失败: {e}")
                    continue

            logger.info(f"批量解析完成: 成功{len(parsed_results)}/{len(announcements)}条")
            return parsed_results

        except Exception as e:
            logger.error(f"批量解析公告失败: {e}")
            return []

    def get_parsing_statistics(self, parsed_announcements: List[ParsedAnnouncement]) -> Dict[str, Any]:
        """获取解析统计信息"""
        try:
            if not parsed_announcements:
                return {}

            # 分类统计
            category_counts = {}
            for parsed in parsed_announcements:
                category = parsed.category
                category_counts[category] = category_counts.get(category, 0) + 1

            # 重要性统计
            importance_counts = {}
            for parsed in parsed_announcements:
                level = parsed.importance_level
                importance_counts[level] = importance_counts.get(level, 0) + 1

            # 情绪统计
            sentiment_counts = {}
            for parsed in parsed_announcements:
                sentiment = parsed.sentiment_label
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

            # 平均置信度
            avg_confidence = sum(p.confidence_score for p in parsed_announcements) / len(parsed_announcements)

            stats = {
                'total_announcements': len(parsed_announcements),
                'category_distribution': category_counts,
                'importance_distribution': importance_counts,
                'sentiment_distribution': sentiment_counts,
                'average_confidence': avg_confidence,
                'high_importance_count': sum(1 for p in parsed_announcements if p.importance_level >= 4),
                'key_metrics_extracted': sum(1 for p in parsed_announcements if p.key_metrics)
            }

            return stats

        except Exception as e:
            logger.error(f"获取解析统计失败: {e}")
            return {}
