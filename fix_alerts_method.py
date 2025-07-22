"""
修复_process_alerts方法中的变量引用错误

问题描述：
在形态分析中，_process_alerts方法中引用了未定义的results变量，导致错误：
NameError: name 'results' is not defined
"""

import os
import sys
import re
import logging

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("alerts_fix.log"),
                              logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("alerts_fix")


def fix_process_alerts_method():
    """修复_process_alerts方法中的变量引用错误"""
    try:
        # 获取pattern_tab.py文件路径
        pattern_tab_path = os.path.join(os.path.dirname(__file__), 'gui', 'widgets', 'analysis_tabs', 'pattern_tab.py')

        if not os.path.exists(pattern_tab_path):
            logger.error(f"找不到文件: {pattern_tab_path}")
            return False

        logger.info(f"正在修复文件: {pattern_tab_path}")

        # 读取文件内容
        with open(pattern_tab_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找_process_alerts方法
        process_alerts_pattern = r'def _process_alerts\(self, alerts\):(.*?)(?=\n    def|\n\n|$)'
        match = re.search(process_alerts_pattern, content, re.DOTALL)

        if not match:
            logger.error("未找到_process_alerts方法")
            return False

        # 获取当前的方法实现
        current_method = match.group(0)
        logger.info(f"找到_process_alerts方法: {current_method}")

        # 创建正确的方法实现
        correct_method = '''
    def _process_alerts(self, alerts):
        """处理预警 - 修复版"""
        try:
            # 检查alerts参数
            if not alerts:
                return
                
            # 发送预警信号
            if hasattr(self, 'pattern_alert'):
                for alert in alerts:
                    self.pattern_alert.emit(alert['type'], alert)
        except Exception as e:
            import traceback
            self.log_manager.error(f"处理预警失败: {e}")
            self.log_manager.error(traceback.format_exc())
'''

        # 替换方法
        new_content = content.replace(current_method, correct_method)

        # 写回文件
        with open(pattern_tab_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        logger.info("成功修复_process_alerts方法")
        return True

    except Exception as e:
        logger.error(f"修复_process_alerts方法失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def check_update_results_display():
    """检查并修复_update_results_display方法中对_process_alerts的调用"""
    try:
        # 获取pattern_tab_pro.py文件路径
        pattern_tab_pro_path = os.path.join(os.path.dirname(__file__), 'gui', 'widgets', 'analysis_tabs', 'pattern_tab_pro.py')

        if not os.path.exists(pattern_tab_pro_path):
            logger.error(f"找不到文件: {pattern_tab_pro_path}")
            return False

        logger.info(f"正在检查_update_results_display方法: {pattern_tab_pro_path}")

        # 读取文件内容
        with open(pattern_tab_pro_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 寻找_update_results_display方法
        update_results_pattern = r'def _update_results_display\(self, results\):(.*?)(?=\n    def )'
        match = re.search(update_results_pattern, content, re.DOTALL)

        if not match:
            logger.error("未找到_update_results_display方法")
            return False

        # 确保安全调用_process_alerts
        if "if hasattr(self, '_process_alerts')" in match.group(1):
            logger.info("_update_results_display方法已包含安全检查，无需修复")
            return True

        # 创建安全版本的方法
        safe_method = '''
    def _update_results_display(self, results):
        """更新结果显示 - 安全版"""
        try:
            # 更新形态表格
            if 'patterns' in results:
                if hasattr(self, '_update_patterns_table'):
                    self._update_patterns_table(results['patterns'])
                else:
                    self.log_manager.warning("对象没有_update_patterns_table方法")

            # 更新AI预测
            if 'predictions' in results:
                if hasattr(self, '_update_predictions_display'):
                    self._update_predictions_display(results['predictions'])
                else:
                    self.log_manager.warning("对象没有_update_predictions_display方法")

            # 更新统计信息
            if 'statistics' in results:
                if hasattr(self, '_update_statistics_display'):
                    self._update_statistics_display(results['statistics'])
                else:
                    self.log_manager.warning("对象没有_update_statistics_display方法")

            # 处理预警
            if 'alerts' in results:
                if hasattr(self, '_process_alerts'):
                    self._process_alerts(results['alerts'])
                else:
                    self.log_manager.warning("对象没有_process_alerts方法")

        except Exception as e:
            import traceback
            self.log_manager.error(f"更新结果显示失败: {e}")
            self.log_manager.error(traceback.format_exc())
'''

        # 替换方法
        new_content = content.replace(match.group(0), safe_method)

        # 写回文件
        with open(pattern_tab_pro_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        logger.info("成功修复_update_results_display方法")
        return True

    except Exception as e:
        logger.error(f"检查_update_results_display方法失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=== 开始修复预警处理方法 ===")

    # 修复_process_alerts方法
    alerts_fixed = fix_process_alerts_method()
    logger.info(f"修复_process_alerts方法结果: {'成功' if alerts_fixed else '失败'}")

    # 检查_update_results_display方法
    results_fixed = check_update_results_display()
    logger.info(f"检查_update_results_display方法结果: {'成功' if results_fixed else '失败'}")

    # 总结
    if alerts_fixed and results_fixed:
        logger.info("修复成功！请重启应用以使修复生效。")
    else:
        logger.warning("修复不完全，请查看日志获取详细信息。")

    logger.info("=== 修复完成 ===")


if __name__ == "__main__":
    main()
