"""
语言切换管理器
专门处理语言切换相关的逻辑，避免UI卡死问题
"""

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker
from PyQt5.QtWidgets import QApplication
from typing import Optional, Callable
import traceback


class LanguageSwitchManager(QObject):
    """语言切换管理器 - 防止UI卡死的专业解决方案"""

    # 信号定义
    language_switch_started = pyqtSignal(str)  # 语言切换开始
    language_switch_completed = pyqtSignal(str)  # 语言切换完成
    language_switch_failed = pyqtSignal(str, str)  # 语言切换失败 (language_code, error_msg)

    def __init__(self, i18n_manager, config_manager, log_manager):
        super().__init__()
        self.i18n_manager = i18n_manager
        self.config_manager = config_manager
        self.log_manager = log_manager

        # 防护机制
        self._switching_mutex = QMutex()
        self._is_switching = False
        self._pending_switch = None

        # 配置保存线程
        self._config_thread = None
        self._init_config_thread()

    def _init_config_thread(self):
        """初始化配置保存线程"""
        try:
            self._config_thread = QThread()
            self._config_thread.start()
            self.log_manager.debug("语言切换管理器配置线程已初始化")
        except Exception as e:
            self.log_manager.error(f"初始化配置线程失败: {str(e)}")

    def switch_language(self, language_code: str, ui_update_callback: Optional[Callable] = None) -> bool:
        """
        切换语言 - 主入口方法

        Args:
            language_code: 目标语言代码
            ui_update_callback: UI更新回调函数

        Returns:
            bool: 是否成功开始切换（不代表切换完成）
        """
        with QMutexLocker(self._switching_mutex):
            try:
                # 检查参数有效性
                if not self._validate_language_code(language_code):
                    return False

                # 检查是否需要切换
                if not self._need_switch(language_code):
                    return True

                # 如果正在切换，记录待处理的切换请求
                if self._is_switching:
                    self._pending_switch = language_code
                    self.log_manager.debug(f"语言切换中，记录待处理请求: {language_code}")
                    return True

                # 开始切换
                self._is_switching = True
                self.language_switch_started.emit(language_code)

                # 异步执行切换流程
                QTimer.singleShot(0, lambda: self._execute_switch(language_code, ui_update_callback))

                return True

            except Exception as e:
                self.log_manager.error(f"开始语言切换失败: {str(e)}")
                self._is_switching = False
                return False

    def _validate_language_code(self, language_code: str) -> bool:
        """验证语言代码"""
        if not language_code or not isinstance(language_code, str):
            self.log_manager.warning(f"无效的语言代码: {language_code}")
            return False

        supported_languages = self.i18n_manager.get_supported_languages()
        if language_code not in supported_languages:
            self.log_manager.warning(f"不支持的语言代码: {language_code}")
            return False

        return True

    def _need_switch(self, language_code: str) -> bool:
        """检查是否需要切换语言"""
        current_language = self.i18n_manager.get_current_language()
        if language_code == current_language:
            self.log_manager.debug(f"语言未变化，跳过切换: {language_code}")
            return False
        return True

    def _execute_switch(self, language_code: str, ui_update_callback: Optional[Callable] = None):
        """执行语言切换的核心逻辑"""
        try:
            current_language = self.i18n_manager.get_current_language()
            self.log_manager.info(f"开始切换语言: {current_language} -> {language_code}")

            # 1. 设置新语言（快速操作）
            self.i18n_manager.set_language(language_code)

            # 2. 异步保存配置
            self._save_config_async(language_code)

            # 3. 更新UI（如果提供了回调）
            if ui_update_callback:
                try:
                    ui_update_callback(language_code)
                except Exception as e:
                    self.log_manager.warning(f"UI更新回调执行失败: {str(e)}")

            # 4. 完成切换
            self._complete_switch(language_code)

        except Exception as e:
            self._handle_switch_error(language_code, str(e))

    def _save_config_async(self, language_code: str):
        """异步保存语言配置"""
        from PyQt5.QtCore import QObject, pyqtSignal

        class ConfigSaveWorker(QObject):
            finished = pyqtSignal(bool, str)

            def __init__(self, config_manager, language_code):
                super().__init__()
                self.config_manager = config_manager
                self.language_code = language_code

            def save(self):
                try:
                    ui_config = self.config_manager.get('ui', {})
                    ui_config['language'] = self.language_code
                    self.config_manager.set('ui', ui_config)
                    self.finished.emit(True, "")
                except Exception as e:
                    self.finished.emit(False, str(e))

        def on_config_saved(success, error_msg):
            if success:
                self.log_manager.debug(f"语言配置已保存: {language_code}")
            else:
                self.log_manager.error(f"保存语言配置失败: {error_msg}")

        # 创建工作对象并移动到配置线程
        worker = ConfigSaveWorker(self.config_manager, language_code)
        worker.moveToThread(self._config_thread)
        worker.finished.connect(on_config_saved)

        # 异步执行保存
        QTimer.singleShot(0, worker.save)

    def _complete_switch(self, language_code: str):
        """完成语言切换"""
        try:
            self.log_manager.info(f"语言切换完成: {language_code}")
            self.language_switch_completed.emit(language_code)

            # 处理待处理的切换请求
            self._process_pending_switch()

        except Exception as e:
            self.log_manager.error(f"完成语言切换时出错: {str(e)}")
        finally:
            self._is_switching = False

    def _handle_switch_error(self, language_code: str, error_msg: str):
        """处理语言切换错误"""
        try:
            self.log_manager.error(f"语言切换失败: {language_code} - {error_msg}")
            self.language_switch_failed.emit(language_code, error_msg)

            # 尝试恢复到之前的语言
            try:
                current_language = self.i18n_manager.get_current_language()
                if current_language != language_code:
                    self.log_manager.info(f"语言已恢复到: {current_language}")
            except Exception as recovery_error:
                self.log_manager.error(f"语言恢复失败: {str(recovery_error)}")

        except Exception as e:
            self.log_manager.error(f"处理语言切换错误时出错: {str(e)}")
        finally:
            self._is_switching = False

    def _process_pending_switch(self):
        """处理待处理的语言切换请求"""
        if self._pending_switch:
            pending_language = self._pending_switch
            self._pending_switch = None

            self.log_manager.debug(f"处理待处理的语言切换请求: {pending_language}")

            # 延迟处理，避免立即重入
            QTimer.singleShot(100, lambda: self.switch_language(pending_language))

    def is_switching(self) -> bool:
        """检查是否正在切换语言"""
        return self._is_switching

    def get_current_language(self) -> str:
        """获取当前语言"""
        return self.i18n_manager.get_current_language()

    def get_supported_languages(self) -> dict:
        """获取支持的语言列表"""
        return self.i18n_manager.get_supported_languages()

    def cleanup(self):
        """清理资源"""
        try:
            if self._config_thread and self._config_thread.isRunning():
                self._config_thread.quit()
                self._config_thread.wait(3000)  # 等待最多3秒
                if self._config_thread.isRunning():
                    self._config_thread.terminate()
                    self._config_thread.wait(1000)

            self.log_manager.debug("语言切换管理器资源已清理")

        except Exception as e:
            self.log_manager.error(f"清理语言切换管理器资源失败: {str(e)}")


# 全局单例
_language_switch_manager = None


def get_language_switch_manager(i18n_manager=None, config_manager=None, log_manager=None):
    """获取语言切换管理器单例"""
    global _language_switch_manager

    if _language_switch_manager is None:
        if not all([i18n_manager, config_manager, log_manager]):
            raise ValueError("首次创建语言切换管理器需要提供所有参数")

        _language_switch_manager = LanguageSwitchManager(
            i18n_manager, config_manager, log_manager
        )

    return _language_switch_manager


def cleanup_language_switch_manager():
    """清理语言切换管理器"""
    global _language_switch_manager

    if _language_switch_manager:
        _language_switch_manager.cleanup()
        _language_switch_manager = None
