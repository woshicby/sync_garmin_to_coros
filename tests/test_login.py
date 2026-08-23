#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Garmin 登录逻辑测试：token 失效回退、密码重试、异常退出"""

import sys
from unittest import mock

import pytest

from core import downloader


class FakeAuthError(Exception):
    """模拟 garminconnect.GarminConnectAuthenticationError"""


def _make_fake_module():
    fm = mock.MagicMock()
    fm.GarminConnectAuthenticationError = FakeAuthError
    return fm


def _make_fake_config_manager():
    """返回 no-op 的配置管理器（防止测试写入真实 config 文件）"""
    cm = mock.MagicMock()
    cm.load.return_value = {'email': 'test@example.com'}
    return cm


@pytest.fixture
def env():
    """mock garminconnect/garth 与配置管理器"""
    fm = _make_fake_module()
    cm = _make_fake_config_manager()
    with mock.patch.object(downloader, 'get_garmin_config', return_value=cm), \
         mock.patch.dict(sys.modules, {'garminconnect': fm, 'garth': mock.MagicMock()}):
        yield fm, cm


def _make_client_with_login_side_effect(side_effect):
    client = mock.MagicMock()
    client.login.side_effect = side_effect
    return client


def test_token_invalid_falls_back_to_password(env):
    """token 失效 → 提示并回退到密码登录, 密码正确则成功"""
    fm, cm = env
    calls = {'n': 0}

    def login_side(*a, **kw):
        calls['n'] += 1
        if calls['n'] == 1:
            raise FakeAuthError('token expired')
        return None

    client = _make_client_with_login_side_effect(login_side)
    fm.Garmin.return_value = client

    with mock.patch('builtins.input', side_effect=['correct_pw']):
        result = downloader._login_garmin()

    assert result is client, "密码登录成功后应返回 client"
    assert calls['n'] == 2, f"应调用 2 次 login（token 失败 + 密码成功），实际 {calls['n']}"
    cm.save.assert_called_once(), "登录成功应保存新凭据"


def test_password_wrong_retries_then_success(env):
    """密码错误可重试：错 2 次后第 3 次成功"""
    fm, cm = env
    calls = {'n': 0}

    def login_side(*a, **kw):
        calls['n'] += 1
        if calls['n'] <= 2:
            raise FakeAuthError('bad password')
        return None

    client = _make_client_with_login_side_effect(login_side)
    fm.Garmin.return_value = client

    with mock.patch('builtins.input', side_effect=['wrong1', 'wrong2', 'right']):
        result = downloader._login_garmin()

    assert result is client
    assert calls['n'] == 3, f"应尝试 3 次，实际 {calls['n']}"


def test_non_auth_error_aborts_without_retry(env):
    """token 失效后, 密码登录遇非认证错误（网络）→ 不重试, 返回 None"""
    fm, cm = env
    calls = {'n': 0}

    def login_side(*a, **kw):
        calls['n'] += 1
        if calls['n'] == 1:
            raise FakeAuthError('token expired')  # token 失效 → 进入密码循环
        raise ConnectionError('network down')     # 密码登录遇网络错误

    client = _make_client_with_login_side_effect(login_side)
    fm.Garmin.return_value = client

    with mock.patch('builtins.input', side_effect=['pw']):
        result = downloader._login_garmin()

    assert result is None, "网络错误应返回 None"
    # token 分支 1 次 + 密码分支 1 次；密码分支失败后不重试
    assert calls['n'] == 2, f"不应重试，实际 {calls['n']}"


def test_input_exhausted_aborts_without_loop(env):
    """输入流耗尽（非交互环境）→ 取消登录, 不死循环"""
    fm, cm = env
    client = _make_client_with_login_side_effect(FakeAuthError('bad'))
    fm.Garmin.return_value = client

    with mock.patch('builtins.input', side_effect=['pw1']):
        result = downloader._login_garmin()

    assert result is None, "输入耗尽应返回 None（不死循环）"


def test_keyboard_interrupt_aborts(env):
    """用户 Ctrl+C → 取消登录"""
    fm, cm = env
    client = _make_client_with_login_side_effect(FakeAuthError('bad'))
    fm.Garmin.return_value = client

    with mock.patch('builtins.input', side_effect=KeyboardInterrupt):
        result = downloader._login_garmin()

    assert result is None, "Ctrl+C 应取消登录"
