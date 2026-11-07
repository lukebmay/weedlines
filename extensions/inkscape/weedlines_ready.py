# -*- coding: utf-8 -*-
"""Make ready to cut: spawn the check and return at once.

The effect does not change the open document. The child calls
``build_correction_marks`` and writes the ready file through
``write_correction_svg`` only when a defect is present.
"""
from __future__ import division

import json
import os
import sys
import time


def _ensure_paths():
    ext_dir = os.path.abspath(os.path.dirname(__file__))
    if ext_dir not in sys.path:
        sys.path.insert(0, ext_dir)
    try:
        import weedlib  # noqa: F401
        return
    except ImportError:
        pass
    root = os.path.abspath(os.path.join(ext_dir, '..', '..'))
    src = os.path.join(root, 'src')
    if os.path.isdir(os.path.join(src, 'weedlib')) and src not in sys.path:
        sys.path.insert(0, src)


def write_ready_job(records, doc_attrs):
    """Snapshot the records for the detached check."""
    from weedlines_job import cache_dir

    payload = {
        'records': list(records or []),
        'doc_attrs': dict(doc_attrs or {}),
    }
    path = os.path.join(
        cache_dir(), 'ready-%d.json' % int(time.time() * 1000))
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh)
    os.replace(tmp, path)
    return path


def spawn_ready(job_path):
    """Detach the check so the effect's exit does not kill it."""
    from weedlines_job import spawn_detached

    return spawn_detached(
        'weedlines_ready.py',
        ['--ready-job', os.path.abspath(job_path)],
        log_name='ready.log',
    )


def apply_ready(records, doc_attrs=None):
    """Write the ready file when the check has a defect.

    A clear check writes nothing and removes a stale ready file.
    """
    from weedlib.ready import build_correction_marks
    from weedlines_job import ready_svg_file
    from weedlines_svg import write_correction_svg

    marks = build_correction_marks(records)
    path = ready_svg_file()
    if marks.check.defects:
        write_correction_svg(
            marks.arrows,
            doc_attrs=doc_attrs,
            path=path,
            labels=marks.labels,
        )
        return path
    if os.path.isfile(path):
        os.remove(path)
    return None


def run_ready_job(path):
    with open(path, 'r', encoding='utf-8') as fh:
        payload = json.load(fh)
    return apply_ready(
        payload.get('records') or [],
        payload.get('doc_attrs') or {},
    )


def _selected_nodes(svg):
    selection = getattr(svg, 'selection', None)
    values = getattr(selection, 'values', None) if selection is not None else None
    if callable(values):
        nodes = list(values())
        if nodes:
            return nodes
    return [svg]


class ReadyEffect(object):
    """Inkscape effect. The open document is not applied."""

    def add_arguments(self, pars):
        pars.add_argument('--tab', type=str, default='')

    def has_changed(self, ret):
        # This Inkscape saves when the document bytes differ and ignores
        # the effect return. The check must not apply a document change.
        return False

    def effect(self):
        import inkex

        _ensure_paths()
        ext_dir = os.path.abspath(os.path.dirname(__file__))
        if ext_dir not in sys.path:
            sys.path.insert(0, ext_dir)

        from weedlib.qt import QTransform
        from weedlines import _path_records
        from weedlines_svg import doc_root_attrs

        try:
            records = _path_records(
                _selected_nodes(self.svg), inkex, QTransform)
        except Exception as exc:
            raise inkex.AbortExtension(
                'weedlib / Qt not available: {}'.format(exc))
        doc_attrs = doc_root_attrs(self.svg)
        job_path = write_ready_job(records, doc_attrs)
        old_err = sys.stderr
        try:
            sys.stderr = open(os.devnull, 'w')
            try:
                spawn_ready(job_path)
            except Exception as exc:
                sys.stderr = old_err
                raise inkex.AbortExtension(
                    'Could not start the ready check: {}'.format(exc))
        finally:
            try:
                if sys.stderr is not old_err:
                    sys.stderr.close()
            except Exception:
                pass
            sys.stderr = old_err
        return False


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--ready-job' in argv:
        _ensure_paths()
        index = argv.index('--ready-job')
        run_ready_job(argv[index + 1])
        return 0

    try:
        import inkex
    except ImportError:
        sys.stderr.write('inkex not installed.\n')
        sys.exit(2)

    _ensure_paths()
    base = getattr(inkex, 'EffectExtension', None) or inkex.Effect

    class _Plugin(ReadyEffect, base):
        pass

    _Plugin().run(argv)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
