import openai
import threading
import time
from utils.notification import send_notification
from core.logger import LogManager


class AIAlert:
    def __init__(self, api_key: str, log_manager=None):
        self.api_key = api_key
        self.log_manager = log_manager or LogManager()
        openai.api_key = api_key
        self.alert_history = []
        self.running = False

    def parse_condition(self, user_input: str) -> dict:
        prompt = f"请将以下预警条件转为结构化规则JSON：{user_input}"
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            import json
            return json.loads(resp['choices'][0]['message']['content'])
        except Exception as e:
            self.log_manager.error(f"LLM解析预警条件失败: {e}")
            return {}

    def start_alert(self, user_input: str, push_type: str):
        condition = self.parse_condition(user_input)
        if not condition:
            return {"error": "预警条件解析失败"}
        self.running = True

        def monitor():
            while self.running:
                try:
                    # TODO: 实现具体检测逻辑
                    triggered = False  # 检测逻辑
                    if triggered:
                        send_notification(push_type, f"预警触发: {user_input}")
                        self.alert_history.append({"condition": user_input, "push_type": push_type, "time": time.strftime('%Y-%m-%d %H:%M:%S')})
                except Exception as e:
                    self.log_manager.error(f"预警检测异常: {e}")
                time.sleep(60)
        threading.Thread(target=monitor, daemon=True).start()
        return {"status": "预警已启动"}

    def stop_alert(self):
        self.running = False
        return {"status": "预警已停止"}

    def get_history(self):
        return self.alert_history
