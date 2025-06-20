"""
国际化支持模块
支持多语言界面，包括中文和英文
"""
import os
import json
import gettext
from typing import Dict, Optional
from pathlib import Path


class I18nManager:
    """国际化管理器"""

    def __init__(self, locale_dir: str = "locales", default_language: str = "zh_CN"):
        """
        初始化国际化管理器

        Args:
            locale_dir: 语言文件目录
            default_language: 默认语言
        """
        self.locale_dir = Path(locale_dir)
        self.locale_dir.mkdir(exist_ok=True)
        self.default_language = default_language
        self.current_language = default_language

        # 支持的语言
        self.supported_languages = {
            "zh_CN": "简体中文",
            "en_US": "English",
            "zh_TW": "繁體中文",
            "ja_JP": "日本語"
        }

        # 翻译字典
        self.translations: Dict[str, Dict[str, str]] = {}

        # 加载翻译文件
        self.load_translations()

        # 设置当前语言
        self.set_language(default_language)

    def load_translations(self):
        """加载所有翻译文件"""
        for lang_code in self.supported_languages:
            lang_file = self.locale_dir / f"{lang_code}.json"
            if lang_file.exists():
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"加载语言文件失败 {lang_file}: {e}")
                    self.translations[lang_code] = {}
            else:
                # 创建默认翻译文件
                self.translations[lang_code] = self._get_default_translations(lang_code)
                self._save_translation_file(lang_code)

    def _get_default_translations(self, lang_code: str) -> Dict[str, str]:
        """获取默认翻译"""
        if lang_code == "zh_CN":
            return {
                # 主界面
                "main_window_title": "HIkyuu量化交易系统",
                "file_menu": "文件",
                "edit_menu": "编辑",
                "view_menu": "视图",
                "tools_menu": "工具",
                "help_menu": "帮助",

                # 文件菜单
                "new_file": "新建",
                "open_file": "打开",
                "save_file": "保存",
                "save_as": "另存为",
                "recent_files": "最近文件",
                "exit": "退出",

                # 编辑菜单
                "undo": "撤销",
                "redo": "重做",
                "cut": "剪切",
                "copy": "复制",
                "paste": "粘贴",
                "select_all": "全选",
                "find": "查找",
                "replace": "替换",

                # 视图菜单
                "zoom_in": "放大",
                "zoom_out": "缩小",
                "zoom_reset": "重置缩放",
                "fullscreen": "全屏",
                "show_toolbar": "显示工具栏",
                "show_statusbar": "显示状态栏",

                # 工具菜单
                "preferences": "首选项",
                "options": "选项",
                "plugins": "插件",
                "calculator": "计算器",
                "converter": "单位转换",

                # 帮助菜单
                "help_contents": "帮助内容",
                "keyboard_shortcuts": "键盘快捷键",
                "about": "关于",
                "check_updates": "检查更新",

                # 股票相关
                "stock_list": "股票列表",
                "stock_code": "股票代码",
                "stock_name": "股票名称",
                "current_price": "当前价格",
                "price_change": "涨跌额",
                "price_change_percent": "涨跌幅",
                "volume": "成交量",
                "market_cap": "市值",
                "pe_ratio": "市盈率",
                "pb_ratio": "市净率",

                # 技术指标
                "technical_indicators": "技术指标",
                "moving_average": "移动平均线",
                "macd": "MACD",
                "rsi": "RSI",
                "bollinger_bands": "布林带",
                "kdj": "KDJ",
                "volume_indicators": "成交量指标",

                # 图表
                "chart": "图表",
                "candlestick_chart": "K线图",
                "line_chart": "线图",
                "bar_chart": "柱状图",
                "volume_chart": "成交量图",
                "time_period": "时间周期",
                "daily": "日线",
                "weekly": "周线",
                "monthly": "月线",
                "minute": "分钟线",

                # 分析
                "analysis": "分析",
                "technical_analysis": "技术分析",
                "fundamental_analysis": "基本面分析",
                "quantitative_analysis": "量化分析",
                "risk_analysis": "风险分析",
                "portfolio_analysis": "组合分析",

                # 交易
                "trading": "交易",
                "buy": "买入",
                "sell": "卖出",
                "position": "持仓",
                "order": "订单",
                "portfolio": "投资组合",
                "profit_loss": "盈亏",
                "commission": "佣金",
                "slippage": "滑点",

                # 策略
                "strategy": "策略",
                "backtest": "回测",
                "optimization": "优化",
                "parameter": "参数",
                "performance": "业绩",
                "sharpe_ratio": "夏普比率",
                "max_drawdown": "最大回撤",
                "annual_return": "年化收益率",

                # 数据
                "data": "数据",
                "data_source": "数据源",
                "update_data": "更新数据",
                "export_data": "导出数据",
                "import_data": "导入数据",
                "data_quality": "数据质量",

                # 设置
                "settings": "设置",
                "general_settings": "常规设置",
                "display_settings": "显示设置",
                "data_settings": "数据设置",
                "trading_settings": "交易设置",
                "alert_settings": "提醒设置",

                # 状态和消息
                "status": "状态",
                "ready": "就绪",
                "loading": "加载中...",
                "processing": "处理中...",
                "completed": "完成",
                "error": "错误",
                "warning": "警告",
                "information": "信息",
                "success": "成功",
                "failed": "失败",

                # 按钮
                "ok": "确定",
                "cancel": "取消",
                "apply": "应用",
                "close": "关闭",
                "yes": "是",
                "no": "否",
                "save": "保存",
                "load": "加载",
                "delete": "删除",
                "add": "添加",
                "remove": "移除",
                "edit": "编辑",
                "refresh": "刷新",
                "reset": "重置",

                # 时间
                "today": "今天",
                "yesterday": "昨天",
                "this_week": "本周",
                "last_week": "上周",
                "this_month": "本月",
                "last_month": "上月",
                "this_year": "今年",
                "last_year": "去年",

                # 单位
                "yuan": "元",
                "million": "百万",
                "billion": "十亿",
                "percent": "百分比",
                "shares": "股",
                "lots": "手",

                # 错误消息
                "file_not_found": "文件未找到",
                "access_denied": "访问被拒绝",
                "network_error": "网络错误",
                "data_error": "数据错误",
                "calculation_error": "计算错误",
                "invalid_input": "输入无效",
                "operation_failed": "操作失败",
                "timeout_error": "超时错误"
            }

        elif lang_code == "en_US":
            return {
                # Main interface
                "main_window_title": "HIkyuu Quantitative Trading System",
                "file_menu": "File",
                "edit_menu": "Edit",
                "view_menu": "View",
                "tools_menu": "Tools",
                "help_menu": "Help",

                # File menu
                "new_file": "New",
                "open_file": "Open",
                "save_file": "Save",
                "save_as": "Save As",
                "recent_files": "Recent Files",
                "exit": "Exit",

                # Edit menu
                "undo": "Undo",
                "redo": "Redo",
                "cut": "Cut",
                "copy": "Copy",
                "paste": "Paste",
                "select_all": "Select All",
                "find": "Find",
                "replace": "Replace",

                # View menu
                "zoom_in": "Zoom In",
                "zoom_out": "Zoom Out",
                "zoom_reset": "Reset Zoom",
                "fullscreen": "Fullscreen",
                "show_toolbar": "Show Toolbar",
                "show_statusbar": "Show Status Bar",

                # Tools menu
                "preferences": "Preferences",
                "options": "Options",
                "plugins": "Plugins",
                "calculator": "Calculator",
                "converter": "Unit Converter",

                # Help menu
                "help_contents": "Help Contents",
                "keyboard_shortcuts": "Keyboard Shortcuts",
                "about": "About",
                "check_updates": "Check for Updates",

                # Stock related
                "stock_list": "Stock List",
                "stock_code": "Stock Code",
                "stock_name": "Stock Name",
                "current_price": "Current Price",
                "price_change": "Price Change",
                "price_change_percent": "Change %",
                "volume": "Volume",
                "market_cap": "Market Cap",
                "pe_ratio": "P/E Ratio",
                "pb_ratio": "P/B Ratio",

                # Technical indicators
                "technical_indicators": "Technical Indicators",
                "moving_average": "Moving Average",
                "macd": "MACD",
                "rsi": "RSI",
                "bollinger_bands": "Bollinger Bands",
                "kdj": "KDJ",
                "volume_indicators": "Volume Indicators",

                # Charts
                "chart": "Chart",
                "candlestick_chart": "Candlestick Chart",
                "line_chart": "Line Chart",
                "bar_chart": "Bar Chart",
                "volume_chart": "Volume Chart",
                "time_period": "Time Period",
                "daily": "Daily",
                "weekly": "Weekly",
                "monthly": "Monthly",
                "minute": "Minute",

                # Analysis
                "analysis": "Analysis",
                "technical_analysis": "Technical Analysis",
                "fundamental_analysis": "Fundamental Analysis",
                "quantitative_analysis": "Quantitative Analysis",
                "risk_analysis": "Risk Analysis",
                "portfolio_analysis": "Portfolio Analysis",

                # Trading
                "trading": "Trading",
                "buy": "Buy",
                "sell": "Sell",
                "position": "Position",
                "order": "Order",
                "portfolio": "Portfolio",
                "profit_loss": "P&L",
                "commission": "Commission",
                "slippage": "Slippage",

                # Strategy
                "strategy": "Strategy",
                "backtest": "Backtest",
                "optimization": "Optimization",
                "parameter": "Parameter",
                "performance": "Performance",
                "sharpe_ratio": "Sharpe Ratio",
                "max_drawdown": "Max Drawdown",
                "annual_return": "Annual Return",

                # Data
                "data": "Data",
                "data_source": "Data Source",
                "update_data": "Update Data",
                "export_data": "Export Data",
                "import_data": "Import Data",
                "data_quality": "Data Quality",

                # Settings
                "settings": "Settings",
                "general_settings": "General Settings",
                "display_settings": "Display Settings",
                "data_settings": "Data Settings",
                "trading_settings": "Trading Settings",
                "alert_settings": "Alert Settings",

                # Status and messages
                "status": "Status",
                "ready": "Ready",
                "loading": "Loading...",
                "processing": "Processing...",
                "completed": "Completed",
                "error": "Error",
                "warning": "Warning",
                "information": "Information",
                "success": "Success",
                "failed": "Failed",

                # Buttons
                "ok": "OK",
                "cancel": "Cancel",
                "apply": "Apply",
                "close": "Close",
                "yes": "Yes",
                "no": "No",
                "save": "Save",
                "load": "Load",
                "delete": "Delete",
                "add": "Add",
                "remove": "Remove",
                "edit": "Edit",
                "refresh": "Refresh",
                "reset": "Reset",

                # Time
                "today": "Today",
                "yesterday": "Yesterday",
                "this_week": "This Week",
                "last_week": "Last Week",
                "this_month": "This Month",
                "last_month": "Last Month",
                "this_year": "This Year",
                "last_year": "Last Year",

                # Units
                "yuan": "Yuan",
                "million": "Million",
                "billion": "Billion",
                "percent": "Percent",
                "shares": "Shares",
                "lots": "Lots",

                # Error messages
                "file_not_found": "File Not Found",
                "access_denied": "Access Denied",
                "network_error": "Network Error",
                "data_error": "Data Error",
                "calculation_error": "Calculation Error",
                "invalid_input": "Invalid Input",
                "operation_failed": "Operation Failed",
                "timeout_error": "Timeout Error"
            }

        else:
            # 对于其他语言，返回英文作为默认
            return self._get_default_translations("en_US")

    def _save_translation_file(self, lang_code: str):
        """保存翻译文件"""
        lang_file = self.locale_dir / f"{lang_code}.json"
        try:
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(self.translations[lang_code], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存语言文件失败 {lang_file}: {e}")

    def set_language(self, lang_code: str):
        """
        设置当前语言

        Args:
            lang_code: 语言代码
        """
        if lang_code in self.supported_languages:
            self.current_language = lang_code
        else:
            print(f"不支持的语言: {lang_code}")
            self.current_language = self.default_language

    def get_text(self, key: str, default: Optional[str] = None) -> str:
        """
        获取翻译文本

        Args:
            key: 翻译键
            default: 默认文本

        Returns:
            翻译后的文本
        """
        if self.current_language in self.translations:
            translation = self.translations[self.current_language].get(key)
            if translation:
                return translation

        # 如果当前语言没有翻译，尝试使用默认语言
        if self.default_language in self.translations:
            translation = self.translations[self.default_language].get(key)
            if translation:
                return translation

        # 如果都没有，返回默认值或键名
        return default if default is not None else key

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.supported_languages.copy()

    def get_current_language(self) -> str:
        """获取当前语言"""
        return self.current_language

    def add_translation(self, lang_code: str, key: str, value: str):
        """
        添加翻译

        Args:
            lang_code: 语言代码
            key: 翻译键
            value: 翻译值
        """
        if lang_code not in self.translations:
            self.translations[lang_code] = {}

        self.translations[lang_code][key] = value
        self._save_translation_file(lang_code)

    def remove_translation(self, lang_code: str, key: str):
        """
        移除翻译

        Args:
            lang_code: 语言代码
            key: 翻译键
        """
        if lang_code in self.translations and key in self.translations[lang_code]:
            del self.translations[lang_code][key]
            self._save_translation_file(lang_code)

    def export_translations(self, export_path: str, lang_code: Optional[str] = None):
        """
        导出翻译文件

        Args:
            export_path: 导出路径
            lang_code: 语言代码，如果为None则导出所有语言
        """
        try:
            if lang_code:
                # 导出指定语言
                if lang_code in self.translations:
                    with open(export_path, 'w', encoding='utf-8') as f:
                        json.dump(self.translations[lang_code], f, indent=2, ensure_ascii=False)
            else:
                # 导出所有语言
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(self.translations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"导出翻译文件失败: {e}")

    def import_translations(self, import_path: str, lang_code: Optional[str] = None):
        """
        导入翻译文件

        Args:
            import_path: 导入路径
            lang_code: 语言代码，如果为None则导入所有语言
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if lang_code:
                # 导入指定语言
                if isinstance(data, dict):
                    self.translations[lang_code] = data
                    self._save_translation_file(lang_code)
            else:
                # 导入所有语言
                if isinstance(data, dict):
                    for code, translations in data.items():
                        if code in self.supported_languages and isinstance(translations, dict):
                            self.translations[code] = translations
                            self._save_translation_file(code)
        except Exception as e:
            print(f"导入翻译文件失败: {e}")


# 全局国际化管理器实例
_i18n_manager = None


def get_i18n_manager() -> I18nManager:
    """获取国际化管理器单例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


def _(key: str, default: Optional[str] = None) -> str:
    """
    快捷翻译函数

    Args:
        key: 翻译键
        default: 默认文本

    Returns:
        翻译后的文本
    """
    return get_i18n_manager().get_text(key, default)


def set_language(lang_code: str):
    """设置当前语言"""
    get_i18n_manager().set_language(lang_code)


def get_supported_languages() -> Dict[str, str]:
    """获取支持的语言列表"""
    return get_i18n_manager().get_supported_languages()


def get_current_language() -> str:
    """获取当前语言"""
    return get_i18n_manager().get_current_language()


# 导出的公共接口
__all__ = [
    'I18nManager',
    'get_i18n_manager',
    '_',
    'set_language',
    'get_supported_languages',
    'get_current_language'
]
