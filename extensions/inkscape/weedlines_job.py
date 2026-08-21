# -*- coding: utf-8 -*-
"""Job / result cache for the detached Weedlines host process.

Inkscape EffectExtensions block the app until the script exits. We write a
job file, spawn ``weedlines_host.py`` in its own session, and return so
Inkscape stays usable. Apply in the host writes a result file; the Import
extension pulls that layer into the open document.
"""
from __future__ import division

import json
import os
import subprocess
import sys
import time


_RESULT_NAME = 'last_result.json'
_RESULT_SVG_NAME = 'last_result.svg'
_JOB_PREFIX = 'job-'


def cache_dir():
    """User cache directory for Weedlines job/result files."""
    xdg = os.environ.get('XDG_CACHE_HOME')
    if xdg:
        base = os.path.join(xdg, 'weedlines')
    elif sys.platform == 'win32':
        base = os.path.join(
            os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
            'weedlines', 'cache')
    elif sys.platform == 'darwin':
        base = os.path.join(
            os.path.expanduser('~'), 'Library', 'Caches', 'weedlines')
    else:
        base = os.path.join(os.path.expanduser('~'), '.cache', 'weedlines')
    try:
        os.makedirs(base, exist_ok=True)
    except TypeError:
        # py2-style exist_ok fallback (not expected under Inkscape 1.x)
        if not os.path.isdir(base):
            os.makedirs(base)
    return base


def result_path():
    return os.path.join(cache_dir(), _RESULT_NAME)


def result_svg_file():
    return os.path.join(cache_dir(), _RESULT_SVG_NAME)


def write_job(keep_d, defaults, doc_attrs=None):
    """Persist keep geometry + dialog defaults; return job file path.

    *doc_attrs* (width/height/viewBox) are copied into the result SVG so
    import keeps the same physical size as the Inkscape document.
    """
    job = {
        'version': 2,
        'created': time.time(),
        'keep_d': keep_d or '',
        'defaults': dict(defaults or {}),
        'doc_attrs': dict(doc_attrs or {}),
    }
    path = os.path.join(
        cache_dir(), '%s%d.json' % (_JOB_PREFIX, int(time.time() * 1000)))
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(job, fh, indent=0)
    return path


def read_job(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def write_result(layer_name, path_d_list, meta=None, keep_d=None,
                 doc_attrs=None):
    """Save Apply output: JSON metadata + SVG (design + cuts)."""
    payload = {
        'version': 2,
        'created': time.time(),
        'layer_name': layer_name or 'Weed lines',
        'paths': list(path_d_list or []),
        'keep_d': keep_d or '',
        'doc_attrs': dict(doc_attrs or {}),
        'meta': dict(meta or {}),
        'svg': _RESULT_SVG_NAME,
    }
    path = result_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=0)
    os.replace(tmp, path)

    try:
        from weedlines_svg import write_result_svg
        write_result_svg(
            keep_d=keep_d,
            weed_d_list=path_d_list,
            doc_attrs=doc_attrs,
            layer_name=layer_name,
            path=result_svg_file(),
        )
    except Exception:
        # JSON alone still allows cut-only import.
        pass
    return path


def read_result(path=None):
    path = path or result_path()
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def spawn_host(job_path):
    """Launch ``weedlines_host.py`` fully detached from Inkscape.

    Must not leave a live ``Popen`` that Python warns about on GC —
    Inkscape treats that ``ResourceWarning`` as extension stderr
    ("received additional data from the script").
    """
    here = os.path.abspath(os.path.dirname(__file__))
    host = os.path.join(here, 'weedlines_host.py')
    if not os.path.isfile(host):
        raise RuntimeError('weedlines_host.py missing next to extension')

    env = os.environ.copy()
    # Prefer the same interpreter Inkscape used for this extension.
    cmd = [sys.executable, host, os.path.abspath(job_path)]

    import warnings

    log_path = os.path.join(cache_dir(), 'host.log')
    log_fh = open(log_path, 'wb')
    try:
        popen_kw = {
            'cwd': here,
            'env': env,
            'stdin': subprocess.DEVNULL,
            'stdout': log_fh,
            'stderr': subprocess.STDOUT,
            'close_fds': True,
        }
        if sys.platform == 'win32':
            # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            popen_kw['creationflags'] = 0x00000008 | 0x00000200
        else:
            popen_kw['start_new_session'] = True

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', ResourceWarning)
            proc = subprocess.Popen(cmd, **popen_kw)
            # Fire-and-forget: non-None returncode stops subprocess.__del__
            # from emitting ResourceWarning → Inkscape "additional data".
            if getattr(proc, 'returncode', None) is None:
                proc.returncode = 0
            del proc
    finally:
        try:
            log_fh.close()
        except Exception:
            pass
    return None
