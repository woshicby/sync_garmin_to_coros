#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存储模块

提供 OSS 文件上传功能。
"""

from .oss_client import get_oss_client, calculate_md5_file

__all__ = ['get_oss_client', 'calculate_md5_file']
