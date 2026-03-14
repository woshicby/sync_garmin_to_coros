#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 客户端模块

提供 Garmin 和 Coros 的 API 客户端。
"""

from .coros_client import CorosClient, CorosLoginError, login_coros

__all__ = ['CorosClient', 'CorosLoginError', 'login_coros']
