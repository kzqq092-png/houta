# 合并自ui/StockScreeningWidget的参数UI和多线程筛选逻辑
# 1. 增加多线程筛选支持
class ScreeningWorker(QThread):
    """选股工作线程"""
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)

    def __init__(self, screener, params):
        super().__init__()
        self.screener = screener
        self.params = params

    def run(self):
        try:
            results = self.screener.screen_stocks(
                strategy_type=self.params['strategy_type'],
                template=self.params['template'],
                technical_params=self.params['technical'],
                fundamental_params=self.params['fundamental'],
                capital_params=self.params['capital']
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

# 2. 在StockScreenerWidget中集成参数UI和多线程筛选
# ...（合并参数UI控件、start_screening、on_screening_finished、on_screening_error、update_result_table、export_results等方法，风格与BaseAnalysisPanel一致）
