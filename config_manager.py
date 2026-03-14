#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

提供统一的配置加载、保存和管理功能，支持密码加密解密。
"""

import os
import json
import base64
import binascii
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """统一配置管理器
    
    使用单例模式，确保配置只加载一次。
    支持不同类型的配置文件，自动处理密码加密解密。
    """
    
    _instances = {}
    
    def __new__(cls, config_type):
        """单例模式：每个配置类型只创建一个实例"""
        if config_type not in cls._instances:
            cls._instances[config_type] = super().__new__(cls)
            cls._instances[config_type]._initialized = False
        return cls._instances[config_type]
    
    def __init__(self, config_type):
        """初始化配置管理器
        
        Args:
            config_type: 配置类型，如 'garmin', 'coros', 'oss'
        """
        if self._initialized:
            return
            
        self.config_type = config_type
        self.config_file = f"config/{config_type}_config.json"
        self._config = None
        self._initialized = True
    
    def load(self):
        """加载配置文件
        
        Returns:
            dict: 配置字典
        """
        if self._config is not None:
            return self._config
            
        if not os.path.exists(self.config_file):
            logger.debug(f"配置文件不存在: {self.config_file}")
            self._config = {}
            return self._config
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            
            if 'password' in self._config and self._config['password']:
                self._config['password'] = self._decrypt_password(self._config['password'])
                
            logger.debug(f"已加载配置文件: {self.config_file}")
        except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as e:
            logger.warning(f"配置文件解析错误: {e}")
            self._config = {}
            
        return self._config
    
    def save(self, config=None):
        """保存配置文件
        
        Args:
            config: 要保存的配置字典，如果为None则保存当前配置
        """
        if config is not None:
            self._config = config
            
        if self._config is None:
            return
            
        save_config = self._config.copy()
        
        if 'password' in save_config and save_config['password']:
            save_config['password'] = self._encrypt_password(save_config['password'])
            
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(save_config, f, indent=2, ensure_ascii=False)
            
        logger.debug(f"已保存配置文件: {self.config_file}")
    
    def get(self, key, default=None):
        """获取配置项
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        config = self.load()
        return config.get(key, default)
    
    def set(self, key, value):
        """设置配置项
        
        Args:
            key: 配置键
            value: 配置值
        """
        if self._config is None:
            self._config = {}
        self._config[key] = value
    
    def update(self, data):
        """批量更新配置
        
        Args:
            data: 要更新的配置字典
        """
        if self._config is None:
            self._config = {}
        self._config.update(data)
    
    def clear_password(self):
        """清除保存的密码"""
        if self._config and 'password' in self._config:
            del self._config['password']
            self.save()
    
    def reload(self):
        """重新加载配置"""
        self._config = None
        return self.load()
    
    @staticmethod
    def _encrypt_password(password):
        """加密密码（Base64编码）
        
        Args:
            password: 明文密码
            
        Returns:
            str: 加密后的密码
        """
        return base64.b64encode(password.encode('utf-8')).decode('utf-8')
    
    @staticmethod
    def _decrypt_password(encrypted_password):
        """解密密码（Base64解码）
        
        Args:
            encrypted_password: 加密的密码
            
        Returns:
            str: 明文密码
        """
        try:
            padded = encrypted_password + '=' * ((4 - len(encrypted_password) % 4) % 4)
            return base64.b64decode(padded).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError):
            return encrypted_password


def get_garmin_config():
    """获取Garmin配置管理器"""
    return ConfigManager('garmin')


def get_coros_config():
    """获取Coros配置管理器"""
    return ConfigManager('coros')


def get_oss_config():
    """获取OSS配置管理器"""
    return ConfigManager('oss')
