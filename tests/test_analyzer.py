#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析器与类型映射测试"""

from core.analyzer import _find_duplicate_activities
from core.downloader import get_activity_type


def test_find_duplicate_activities_matches_by_datetime():
    """按 datetime 匹配重复活动"""
    garmin_files = [
        {'datetime': '2026-08-14 14:12:19', 'filename': 'garmin_a.fit'},
        {'datetime': '2026-08-15 10:00:00', 'filename': 'garmin_b.fit'},
    ]
    coros_files = [
        {'datetime': '2026-08-14 14:12:19', 'filename': 'coros_a.fit'},
        {'datetime': '2026-08-16 08:00:00', 'filename': 'coros_b.fit'},
    ]

    duplicates = _find_duplicate_activities(garmin_files, coros_files)

    assert len(duplicates) == 1, f"应匹配 1 对，实际 {len(duplicates)}"
    garmin_file, coros_file = duplicates[0]
    assert garmin_file['filename'] == 'garmin_a.fit'
    assert coros_file['filename'] == 'coros_a.fit'


def test_find_duplicate_activities_no_match():
    """无重复时返回空列表"""
    garmin_files = [{'datetime': '2026-08-14 14:12:19', 'filename': 'a.fit'}]
    coros_files = [{'datetime': '2026-08-15 10:00:00', 'filename': 'b.fit'}]

    assert _find_duplicate_activities(garmin_files, coros_files) == []


def test_find_duplicate_activities_empty_inputs():
    """空输入返回空列表"""
    assert _find_duplicate_activities([], []) == []
    assert _find_duplicate_activities([{'datetime': 'x', 'filename': 'a'}], []) == []


def test_get_activity_type_mapping():
    """Coros sportType → 类型名映射"""
    assert get_activity_type(100) == 'running'
    assert get_activity_type(101) == 'treadmill_running'
    assert get_activity_type(600) == 'strength_training'
    assert get_activity_type(400) == 'walking'
    assert get_activity_type(99999) == 'other', "未映射类型应回退 other"
