import os
import json
import traceback

class ConfigManager:
    """Configuration manager"""
    
    def __init__(self):
        """Initialize configuration manager"""
        try:
            # 初始化日志管理器
            self.log_manager = LogManager(LoggingConfig(
                level="DEBUG",
                save_to_file=True,
                log_file='config_manager.log',
                max_bytes=5*1024*1024,  # 5MB
                backup_count=3,
                console_output=True
            ))
            
            # 初始化配置
            self.config = {}
            
            # 加载默认配置
            self.load_default_config()
            
            # 加载用户配置
            self.load_user_config()
            
            # 验证配置
            self.validate_config()
            
            self.log_manager.info("配置管理器初始化完成")
            
        except Exception as e:
            self.log_manager.error(f"初始化失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def load_default_config(self):
        """Load default configuration"""
        try:
            # 加载默认配置
            default_config_path = os.path.join(os.path.dirname(__file__), 'config', 'default_config.json')
            with open(default_config_path, 'r', encoding='utf-8') as f:
                default_config = json.load(f)
                
            # 更新配置
            self.config.update(default_config)
            
            self.log_manager.info("默认配置加载完成")
            
        except Exception as e:
            self.log_manager.error(f"加载默认配置失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def load_user_config(self):
        """Load user configuration"""
        try:
            # 加载用户配置
            user_config_path = os.path.join(os.path.dirname(__file__), 'config', 'user_config.json')
            if os.path.exists(user_config_path):
                with open(user_config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    
                # 更新配置
                self.config.update(user_config)
                
            self.log_manager.info("用户配置加载完成")
            
        except Exception as e:
            self.log_manager.error(f"加载用户配置失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def validate_config(self):
        """Validate configuration"""
        try:
            # 验证配置
            required_keys = ['theme', 'style', 'data_path', 'log_path']
            for key in required_keys:
                if key not in self.config:
                    raise ValueError(f"缺少必需的配置项: {key}")
                    
            self.log_manager.info("配置验证完成")
            
        except Exception as e:
            self.log_manager.error(f"验证配置失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def get_config(self, key: str, default=None):
        """Get configuration value"""
        try:
            return self.config.get(key, default)
        except Exception as e:
            self.log_manager.error(f"获取配置失败: {str(e)}")
            return default
            
    def set_config(self, key: str, value):
        """Set configuration value"""
        try:
            self.config[key] = value
            self.save_user_config()
        except Exception as e:
            self.log_manager.error(f"设置配置失败: {str(e)}")
            
    def save_user_config(self):
        """Save user configuration"""
        try:
            user_config_path = os.path.join(os.path.dirname(__file__), 'config', 'user_config.json')
            with open(user_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
                
            self.log_manager.info("用户配置保存完成")
            
        except Exception as e:
            self.log_manager.error(f"保存用户配置失败: {str(e)}")
            self.log_manager.error(traceback.format_exc()) 