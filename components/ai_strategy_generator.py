import openai
from core.trading_system import run_backtest
from core.logger import LogManager


class AIStrategyGenerator:
    def __init__(self, api_key: str, log_manager=None):
        self.api_key = api_key
        self.log_manager = log_manager or LogManager()
        openai.api_key = api_key

    def generate_code(self, user_input: str) -> str:
        """用LLM将自然语言策略描述转为Python策略代码"""
        prompt = f"请将以下策略描述转为Python策略代码，适配hikyuu策略模板：{user_input}"
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return resp['choices'][0]['message']['content']
        except Exception as e:
            self.log_manager.error(f"LLM生成策略代码失败: {e}")
            return ""

    def ai_backtest(self, user_input: str, params: dict = None) -> dict:
        """AI策略生成与回测主入口"""
        try:
            code = self.generate_code(user_input)
            if not code:
                return {"error": "策略代码生成失败"}
            # 假设run_backtest支持动态策略代码
            result = run_backtest(
                "auto", "AI策略", params or {}, custom_code=code)
            return {"code": code, "result": result}
        except Exception as e:
            self.log_manager.error(f"AI策略生成与回测失败: {e}")
            return {"error": str(e)}
