# -*- coding: utf-8 -*-
"""Job cache directory: app home, then XDG, then the platform default."""
from __future__ import division

import importlib.util
import os
import sys

import pytest


def _load(name, filename):
    path = os.path.join(
        os.path.dirname(__file__), '..', 'extensions', 'inkscape', filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


JOB = _load('weedlines_job_cache_under_test', 'weedlines_job.py')


@pytest.fixture
def user_home(monkeypatch, tmp_path):
    """Home and cache variables stay under tmp. Nothing writes the real cache."""
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    monkeypatch.delenv('WEEDLINES_CACHE_HOME', raising=False)
    monkeypatch.delenv('XDG_CACHE_HOME', raising=False)
    monkeypatch.delenv('LOCALAPPDATA', raising=False)
    return home


@pytest.mark.parametrize('platform', ('linux', 'win32', 'darwin'))
def test_weedlines_cache_home_is_the_directory(
        user_home, monkeypatch, tmp_path, platform):
    monkeypatch.setattr(sys, 'platform', platform)
    chosen = tmp_path / 'chosen'
    monkeypatch.setenv('WEEDLINES_CACHE_HOME', str(chosen))
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path / 'xdg'))
    assert JOB.cache_dir() == str(chosen)


@pytest.mark.parametrize('platform', ('linux', 'win32', 'darwin'))
@pytest.mark.parametrize('blank', (None, ''))
def test_xdg_cache_home_adds_weedlines(
        user_home, monkeypatch, tmp_path, platform, blank):
    monkeypatch.setattr(sys, 'platform', platform)
    if blank is None:
        monkeypatch.delenv('WEEDLINES_CACHE_HOME', raising=False)
    else:
        monkeypatch.setenv('WEEDLINES_CACHE_HOME', blank)
    xdg = tmp_path / 'xdg'
    monkeypatch.setenv('XDG_CACHE_HOME', str(xdg))
    assert JOB.cache_dir() == os.path.join(str(xdg), 'weedlines')


def test_linux_default_is_dot_cache(user_home, monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux')
    assert JOB.cache_dir() == os.path.join(str(user_home), '.cache', 'weedlines')


def test_windows_default_is_localappdata_cache(user_home, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'platform', 'win32')
    local = tmp_path / 'local'
    monkeypatch.setenv('LOCALAPPDATA', str(local))
    assert JOB.cache_dir() == os.path.join(str(local), 'weedlines', 'cache')


def test_windows_without_localappdata_uses_home(user_home, monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert JOB.cache_dir() == os.path.join(str(user_home), 'weedlines', 'cache')


def test_macos_default_is_library_caches(user_home, monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert JOB.cache_dir() == os.path.join(
        str(user_home), 'Library', 'Caches', 'weedlines')


def test_cache_dir_follows_a_later_environment(user_home, monkeypatch, tmp_path):
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    monkeypatch.setenv('WEEDLINES_CACHE_HOME', str(first))
    assert JOB.cache_dir() == str(first)
    monkeypatch.setenv('WEEDLINES_CACHE_HOME', str(second))
    assert JOB.cache_dir() == str(second)
