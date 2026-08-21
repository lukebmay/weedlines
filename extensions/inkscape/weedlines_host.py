# -*- coding: utf-8 -*-
"""Detached Weedlines UI process (spawned by the Inkscape extension).

Runs outside Inkscape's extension wait so the app stays interactive.
On Apply, writes ``last_result.svg`` (design + cuts in document units) and
``last_result.json`` for ``Weedlines → Import last result``.
"""
from __future__ import division

import os
import sys


def _ensure_weedlib_on_path():
    try:
        import weedlib  # noqa: F401
        return
    except ImportError:
        pass
    here = os.path.abspath(os.path.dirname(__file__))
    for _ in range(8):
        for candidate in (os.path.join(here, 'src'), here):
            if os.path.isdir(os.path.join(candidate, 'weedlib')):
                if candidate not in sys.path:
                    sys.path.insert(0, candidate)
                try:
                    import weedlib  # noqa: F401
                    return
                except ImportError:
                    pass
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    src = os.path.join(root, 'src')
    if os.path.isdir(os.path.join(src, 'weedlib')) and src not in sys.path:
        sys.path.insert(0, src)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        sys.stderr.write('usage: weedlines_host.py <job.json>\n')
        return 2

    job_path = os.path.abspath(argv[0])
    ext_dir = os.path.abspath(os.path.dirname(__file__))
    if ext_dir not in sys.path:
        sys.path.insert(0, ext_dir)

    _ensure_weedlib_on_path()

    from weedlines_job import read_job, write_result, result_svg_file
    from weedlines_dialog import run_weedlines_dialog
    from weedlib.svg_paths import (
        svg_d_to_qpainterpath, weed_path_to_open_d_list,
    )
    from weedlib.qt import load_widgets

    job = read_job(job_path)
    keep_d = job.get('keep_d') or ''
    defaults = dict(job.get('defaults') or {})
    doc_attrs = dict(job.get('doc_attrs') or {})
    keep = svg_d_to_qpainterpath(keep_d)
    if keep.isEmpty():
        sys.stderr.write('Weedlines host: empty keep geometry in job.\n')
        return 1

    weed, layer_name = run_weedlines_dialog(
        keep, defaults=defaults, quit_app=False)
    try:
        os.remove(job_path)
    except OSError:
        pass

    if weed is None or weed.isEmpty():
        _QtCore, _QtGui, QtWidgets = load_widgets()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()
        return 0

    paths = weed_path_to_open_d_list(weed)
    write_result(
        layer_name,
        paths,
        meta={
            'mode': defaults.get('mode'),
            'padding': defaults.get('padding'),
            'spacing': defaults.get('spacing'),
            'collar': defaults.get('collar'),
            'n_paths': len(paths),
            'keep_bbox': defaults.get('keep_bbox'),
        },
        keep_d=keep_d,
        doc_attrs=doc_attrs,
    )

    svg_path = result_svg_file()
    try:
        _QtCore, _QtGui, QtWidgets = load_widgets()
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        QtWidgets.QMessageBox.information(
            None,
            'Weedlines',
            'Saved design + weed cuts.\n\n'
            'Back in Inkscape, run:\n'
            'Extensions → Weedlines → Import last result\n\n'
            'That brings in the design and cuts together at the\n'
            'original document size/position.\n\n'
            '(%d cut paths)\n%s' % (len(paths), svg_path),
        )
        if app is not None:
            app.quit()
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
