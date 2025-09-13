from loguru import logger
"""
通知服务 - 邮件和短信发送

支持多种免费API服务商：
- 邮件：Mailgun, SendGrid, Brevo, AhaSend
- 短信：云片, 互亿无线, Twilio, YCloud
"""

import smtplib
import requests
from typing import Dict, List, Optional, Union
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dataclasses import dataclass
from enum import Enum
import json
import base64

logger = logger


class NotificationType(Enum):
    """通知类型"""
    EMAIL = "email"
    SMS = "sms"
    VOICE = "voice"


class NotificationProvider(Enum):
    """通知服务提供商"""
    # 邮件服务商
    MAILGUN = "mailgun"
    SENDGRID = "sendgrid"
    BREVO = "brevo"
    AHASEND = "ahasend"
    SMTP = "smtp"

    # 短信服务商
    YUNPIAN = "yunpian"
    IHUYI = "ihuyi"
    TWILIO = "twilio"
    YCLOUD = "ycloud"
    SMSDOVE = "smsdove"


@dataclass
class NotificationConfig:
    """通知配置"""
    provider: NotificationProvider
    api_key: str
    api_secret: Optional[str] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    base_url: Optional[str] = None
    enabled: bool = True


@dataclass
class NotificationMessage:
    """通知消息"""
    recipient: str
    subject: str
    content: str
    html_content: Optional[str] = None
    sender: Optional[str] = None
    sender_name: Optional[str] = None
    attachments: Optional[List[str]] = None
    template_id: Optional[str] = None
    variables: Optional[Dict] = None


class NotificationService:
    """通知服务主类"""

    def __init__(self):
        self.email_configs: Dict[NotificationProvider, NotificationConfig] = {}
        self.sms_configs: Dict[NotificationProvider, NotificationConfig] = {}
        self.default_email_provider = NotificationProvider.SMTP
        self.default_sms_provider = NotificationProvider.YUNPIAN

        # 初始化默认配置
        self._init_default_configs()

    def _init_default_configs(self):
        """初始化默认配置"""
        # 默认SMTP配置（使用QQ邮箱作为示例）
        self.email_configs[NotificationProvider.SMTP] = NotificationConfig(
            provider=NotificationProvider.SMTP,
            api_key="",  # 邮箱密码或授权码
            sender_email="your_email@qq.com",
            sender_name="FactorWeave-Quant 系统",
            smtp_host="smtp.qq.com",
            smtp_port=587
        )

        # Mailgun免费配置
        self.email_configs[NotificationProvider.MAILGUN] = NotificationConfig(
            provider=NotificationProvider.MAILGUN,
            api_key="",  # Mailgun API Key
            base_url="https://api.mailgun.net/v3/sandbox-xxx.mailgun.org",
            sender_email="noreply@sandbox-xxx.mailgun.org",
            sender_name="FactorWeave-Quant"
        )

        # 云片短信配置
        self.sms_configs[NotificationProvider.YUNPIAN] = NotificationConfig(
            provider=NotificationProvider.YUNPIAN,
            api_key="",  # 云片API Key
            base_url="https://sms.yunpian.com/v2/sms/single_send.json"
        )

    def configure_email_provider(self, provider: NotificationProvider, config: NotificationConfig):
        """配置邮件服务商"""
        self.email_configs[provider] = config
        logger.info(f"邮件服务商 {provider.value} 配置完成")

    def configure_sms_provider(self, provider: NotificationProvider, config: NotificationConfig):
        """配置短信服务商"""
        self.sms_configs[provider] = config
        logger.info(f"短信服务商 {provider.value} 配置完成")

    def send_email(self, message: NotificationMessage,
                   provider: Optional[NotificationProvider] = None) -> bool:
        """发送邮件"""
        try:
            provider = provider or self.default_email_provider

            if provider not in self.email_configs:
                logger.error(f"邮件服务商 {provider.value} 未配置")
                return False

            config = self.email_configs[provider]
            if not config.enabled:
                logger.warning(f"邮件服务商 {provider.value} 已禁用")
                return False

            # 根据不同服务商发送邮件
            if provider == NotificationProvider.SMTP:
                return self._send_smtp_email(message, config)
            elif provider == NotificationProvider.MAILGUN:
                return self._send_mailgun_email(message, config)
            elif provider == NotificationProvider.SENDGRID:
                return self._send_sendgrid_email(message, config)
            elif provider == NotificationProvider.BREVO:
                return self._send_brevo_email(message, config)
            elif provider == NotificationProvider.AHASEND:
                return self._send_ahasend_email(message, config)
            else:
                logger.error(f"不支持的邮件服务商: {provider.value}")
                return False

        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False

    def send_sms(self, message: NotificationMessage,
                 provider: Optional[NotificationProvider] = None) -> bool:
        """发送短信"""
        try:
            provider = provider or self.default_sms_provider

            if provider not in self.sms_configs:
                logger.error(f"短信服务商 {provider.value} 未配置")
                return False

            config = self.sms_configs[provider]
            if not config.enabled:
                logger.warning(f"短信服务商 {provider.value} 已禁用")
                return False

            # 根据不同服务商发送短信
            if provider == NotificationProvider.YUNPIAN:
                return self._send_yunpian_sms(message, config)
            elif provider == NotificationProvider.IHUYI:
                return self._send_ihuyi_sms(message, config)
            elif provider == NotificationProvider.TWILIO:
                return self._send_twilio_sms(message, config)
            elif provider == NotificationProvider.YCLOUD:
                return self._send_ycloud_sms(message, config)
            elif provider == NotificationProvider.SMSDOVE:
                return self._send_smsdove_sms(message, config)
            else:
                logger.error(f"不支持的短信服务商: {provider.value}")
                return False

        except Exception as e:
            logger.error(f"发送短信失败: {e}")
            return False

    def _send_smtp_email(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过SMTP发送邮件"""
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = f"{config.sender_name} <{config.sender_email}>"
            msg['To'] = message.recipient
            msg['Subject'] = message.subject

            # 添加邮件内容
            if message.html_content:
                msg.attach(MIMEText(message.html_content, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(message.content, 'plain', 'utf-8'))

            # 添加附件
            if message.attachments:
                for file_path in message.attachments:
                    try:
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {file_path.split("/")[-1]}'
                            )
                            msg.attach(part)
                    except Exception as e:
                        logger.warning(f"添加附件失败 {file_path}: {e}")

            # 发送邮件
            server = smtplib.SMTP(config.smtp_host, config.smtp_port)
            server.starttls()
            server.login(config.sender_email, config.api_key)
            server.sendmail(config.sender_email, message.recipient, msg.as_string())
            server.quit()

            logger.info(f"SMTP邮件发送成功: {message.recipient}")
            return True

        except Exception as e:
            logger.error(f"SMTP邮件发送失败: {e}")
            return False

    def _send_mailgun_email(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过Mailgun发送邮件"""
        try:
            url = f"{config.base_url}/messages"

            data = {
                "from": f"{config.sender_name} <{config.sender_email}>",
                "to": message.recipient,
                "subject": message.subject,
                "text": message.content
            }

            if message.html_content:
                data["html"] = message.html_content

            response = requests.post(
                url,
                auth=("api", config.api_key),
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Mailgun邮件发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"Mailgun邮件发送失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Mailgun邮件发送异常: {e}")
            return False

    def _send_sendgrid_email(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过SendGrid发送邮件"""
        try:
            url = "https://api.sendgrid.com/v3/mail/send"

            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "personalizations": [{
                    "to": [{"email": message.recipient}]
                }],
                "from": {
                    "email": config.sender_email,
                    "name": config.sender_name
                },
                "subject": message.subject,
                "content": [{
                    "type": "text/html" if message.html_content else "text/plain",
                    "value": message.html_content or message.content
                }]
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 202:
                logger.info(f"SendGrid邮件发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"SendGrid邮件发送失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"SendGrid邮件发送异常: {e}")
            return False

    def _send_brevo_email(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过Brevo发送邮件"""
        try:
            url = "https://api.brevo.com/v3/smtp/email"

            headers = {
                "api-key": config.api_key,
                "Content-Type": "application/json"
            }

            data = {
                "sender": {
                    "name": config.sender_name,
                    "email": config.sender_email
                },
                "to": [{"email": message.recipient}],
                "subject": message.subject,
                "htmlContent": message.html_content or f"<p>{message.content}</p>"
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 201:
                logger.info(f"Brevo邮件发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"Brevo邮件发送失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Brevo邮件发送异常: {e}")
            return False

    def _send_ahasend_email(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过AhaSend发送邮件"""
        try:
            url = "https://api.ahasend.com/v1/email/send"

            headers = {
                "X-Api-Key": config.api_key,
                "Content-Type": "application/json"
            }

            data = {
                "from": {
                    "name": config.sender_name,
                    "email": config.sender_email
                },
                "recipients": [{
                    "email": message.recipient
                }],
                "content": {
                    "subject": message.subject,
                    "text_body": message.content,
                    "html_body": message.html_content or f"<p>{message.content}</p>"
                }
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                logger.info(f"AhaSend邮件发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"AhaSend邮件发送失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"AhaSend邮件发送异常: {e}")
            return False

    def _send_yunpian_sms(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过云片发送短信"""
        try:
            data = {
                "apikey": config.api_key,
                "mobile": message.recipient,
                "text": message.content
            }

            response = requests.post(config.base_url, data=data, timeout=30)
            result = response.json()

            if result.get("code") == 0:
                logger.info(f"云片短信发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"云片短信发送失败: {result.get('msg', '未知错误')}")
                return False

        except Exception as e:
            logger.error(f"云片短信发送异常: {e}")
            return False

    def _send_ihuyi_sms(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过互亿无线发送短信"""
        try:
            import hashlib

            # 互亿无线API参数
            account = config.api_key
            password = config.api_secret
            mobile = message.recipient
            content = message.content

            # 生成签名
            sign = hashlib.md5((account + password + mobile + content).encode('utf-8')).hexdigest()

            data = {
                "account": account,
                "password": password,
                "mobile": mobile,
                "content": content,
                "sign": sign
            }

            response = requests.post(
                "https://106.ihuyi.com/webservice/sms.php?method=Submit",
                data=data,
                timeout=30
            )

            # 解析XML响应
            if "2" in response.text:  # 成功标识
                logger.info(f"互亿无线短信发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"互亿无线短信发送失败: {response.text}")
                return False

        except Exception as e:
            logger.error(f"互亿无线短信发送异常: {e}")
            return False

    def _send_twilio_sms(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过Twilio发送短信"""
        try:
            # Twilio API
            account_sid = config.api_key
            auth_token = config.api_secret

            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

            data = {
                "From": config.sender_email,  # Twilio号码
                "To": message.recipient,
                "Body": message.content
            }

            response = requests.post(
                url,
                auth=(account_sid, auth_token),
                data=data,
                timeout=30
            )

            if response.status_code == 201:
                logger.info(f"Twilio短信发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"Twilio短信发送失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Twilio短信发送异常: {e}")
            return False

    def _send_ycloud_sms(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过YCloud发送短信"""
        try:
            url = "https://api.ycloud.com/v2/sms"

            headers = {
                "X-API-Key": config.api_key,
                "Content-Type": "application/json"
            }

            data = {
                "to": message.recipient,
                "text": message.content
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                logger.info(f"YCloud短信发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"YCloud短信发送失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"YCloud短信发送异常: {e}")
            return False

    def _send_smsdove_sms(self, message: NotificationMessage, config: NotificationConfig) -> bool:
        """通过SMSDove发送短信"""
        try:
            url = "https://www.smsdove.com/api/v1/sms/send"

            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "phone": message.recipient,
                "message": message.content,
                "device_id": config.api_secret  # SMSDove需要设备ID
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                logger.info(f"SMSDove短信发送成功: {message.recipient}")
                return True
            else:
                logger.error(f"SMSDove短信发送失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"SMSDove短信发送异常: {e}")
            return False

    def test_email_config(self, provider: NotificationProvider) -> bool:
        """测试邮件配置"""
        try:
            if provider not in self.email_configs:
                return False

            config = self.email_configs[provider]
            test_message = NotificationMessage(
                recipient=config.sender_email,
                subject="FactorWeave-Quant 邮件配置测试",
                content="这是一封测试邮件，如果您收到此邮件，说明邮件配置正确。"
            )

            return self.send_email(test_message, provider)

        except Exception as e:
            logger.error(f"测试邮件配置失败: {e}")
            return False

    def test_sms_config(self, provider: NotificationProvider, test_phone: str) -> bool:
        """测试短信配置"""
        try:
            if provider not in self.sms_configs:
                return False

            test_message = NotificationMessage(
                recipient=test_phone,
                subject="",
                content="【FactorWeave-Quant】这是一条测试短信，如果您收到此短信，说明短信配置正确。"
            )

            return self.send_sms(test_message, provider)

        except Exception as e:
            logger.error(f"测试短信配置失败: {e}")
            return False

    def get_provider_status(self) -> Dict[str, Dict]:
        """获取所有服务商状态"""
        status = {
            "email_providers": {},
            "sms_providers": {}
        }

        for provider, config in self.email_configs.items():
            status["email_providers"][provider.value] = {
                "enabled": config.enabled,
                "configured": bool(config.api_key),
                "sender": config.sender_email
            }

        for provider, config in self.sms_configs.items():
            status["sms_providers"][provider.value] = {
                "enabled": config.enabled,
                "configured": bool(config.api_key)
            }

        return status


# 全局通知服务实例
notification_service = NotificationService()


def send_alert_notification(alert_type: str, message: str,
                            email_recipients: List[str] = None,
                            sms_recipients: List[str] = None) -> Dict[str, bool]:
    """发送告警通知"""
    results = {"email": [], "sms": []}

    # 发送邮件通知
    if email_recipients:
        for email in email_recipients:
            email_msg = NotificationMessage(
                recipient=email,
                subject=f"【FactorWeave-Quant】{alert_type}告警",
                content=message,
                html_content=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #e74c3c;"> 系统告警通知</h2>
                    <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #e74c3c;">
                        <h3>告警类型：{alert_type}</h3>
                        <p>{message}</p>
                        <p style="color: #666; font-size: 12px;">
                            发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>
                </div>
                """
            )
            success = notification_service.send_email(email_msg)
            results["email"].append({"recipient": email, "success": success})

    # 发送短信通知
    if sms_recipients:
        for phone in sms_recipients:
            sms_msg = NotificationMessage(
                recipient=phone,
                subject="",
                content=f"【FactorWeave-Quant】{alert_type}告警：{message}"
            )
            success = notification_service.send_sms(sms_msg)
            results["sms"].append({"recipient": phone, "success": success})

    return results
