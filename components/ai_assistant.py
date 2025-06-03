import openai
from core.logger import LogManager


class AIAssistant:
    def __init__(self, api_key: str, log_manager=None):
        self.api_key = api_key
        self.log_manager = log_manager or LogManager()
        openai.api_key = api_key
        self.history = []

    def chat(self, user_input: str) -> dict:
        self.history.append({"role": "user", "content": user_input})
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=self.history,
                temperature=0.2
            )
            reply = resp['choices'][0]['message']['content']
            self.history.append({"role": "assistant", "content": reply})
            # TODO: 可扩展意图识别与子模块自动调用
            return {"reply": reply}
        except Exception as e:
            self.log_manager.error(f"AI助手对话失败: {e}")
            return {"error": str(e)}
