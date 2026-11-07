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
_READY_SVG_NAME = 'last_ready.svg'
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


def ready_svg_file():
    """Ready file from 2 Make ready to cut. Not the weed-line result."""
    return os.path.join(cache_dir(), _READY_SVG_NAME)


def write_job(keep_d, defaults, doc_attrs=None, records=None):
    """Persist keep geometry, path records, and dialog defaults.

    *doc_attrs* (width/height/viewBox, the named display unit, and the
    scale of one user unit) stay on the job so import can keep the
    document size. *records* is one dict per path element.
    """
    job = {
        'version': 2,
        'created': time.time(),
        'keep_d': keep_d or '',
        'records': list(records or []),
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
                 doc_attrs=None, weed_line_color=None):
    """Save Apply output: JSON metadata + SVG (design + cuts).

    *weed_line_color* is stored when the caller passes one.
    """
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
    if weed_line_color is not None:
        payload['weed_line_color'] = weed_line_color
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
            weed_line_color=weed_line_color,
        )
    except Exception:
        # JSON alone still allows cut-only import.
        pass
    return path


def write_correction_result(arrows, doc_attrs=None, meta=None, labels=None):
    """Store a correction result. The SVG is the ready file, not the weed lines.

    *arrows* maps dangling, overlap, or self-overlap to shaft/head
    paths. Kinds with no arrows are omitted. *labels* are placed by
    ``write_correction_svg``. No design copy. ``last_result.svg`` is
    left for a weed-line result.
    """
    from weedlines_svg import write_correction_svg

    doc_attrs = dict(doc_attrs or {})
    write_correction_svg(
        arrows, doc_attrs=doc_attrs, path=ready_svg_file(), labels=labels)
    payload = {
        'version': 2,
        'created': time.time(),
        'result': 'correction',
        'doc_attrs': doc_attrs,
        'meta': dict(meta or {}),
        'svg': _READY_SVG_NAME,
    }
    path = result_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=0)
    os.replace(tmp, path)
    return path


def read_result(path=None):
    path = path or result_path()
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def spawn_detached(script_name, args, log_name='host.log'):
    """Launch *script_name* in its own session and return at once.

    Must not leave a live ``Popen`` that Python warns about on GC —
    Inkscape treats that ``ResourceWarning`` as extension stderr
    ("received additional data from the script").
    """
    here = os.path.abspath(os.path.dirname(__file__))
    script = os.path.join(here, script_name)
    if not os.path.isfile(script):
        raise RuntimeError('%s missing next to extension' % script_name)

    env = os.environ.copy()
    cmd = [sys.executable, script] + list(args)

    import warnings

    log_path = os.path.join(cache_dir(), log_name)
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


def spawn_host(job_path):
    """Launch ``weedlines_host.py`` fully detached from Inkscape."""
    return spawn_detached(
        'weedlines_host.py', [os.path.abspath(job_path)], log_name='host.log')
