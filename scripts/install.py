#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install the Weedlines Inkscape extension from this checkout.

Idempotent. Prefer an editable package install so ``import weedlib`` works
from Inkscape's Python, then symlink/copy extension files.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

__version__ = '0.1.0'

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'


def _ensure_src_path() -> None:
    src = str(SRC)
    if src not in sys.path:
        sys.path.insert(0, src)


def _try_editable_install() -> None:
    """Best-effort ``pip install -e .`` so weedlib is importable system-wide."""
    pyproject = ROOT / 'pyproject.toml'
    if not pyproject.is_file():
        return
    try:
        import weedlib  # noqa: F401
        return
    except ImportError:
        pass
    cmd = [
        sys.executable, '-m', 'pip', 'install', '-e', str(ROOT),
        '--quiet', '--disable-pip-version-check',
    ]
    print('weedlib not importable; running: {}'.format(' '.join(cmd)),
          file=sys.stderr)
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        print(
            'warning: editable install failed (exit {}); '
            'extension bootstrap may still find ./src/weedlib.'.format(
                exc.returncode),
            file=sys.stderr,
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='install',
        description='Install the Weedlines Inkscape extension (idempotent).',
    )
    p.add_argument('--version', action='version',
                   version='weedlines-install {}'.format(__version__))
    p.add_argument('--dry-run', action='store_true',
                   help='Print actions without changing the filesystem')
    p.add_argument('--uninstall', action='store_true',
                   help='Remove Weedlines-managed extension links')
    p.add_argument('--copy', action='store_true',
                   help='Copy files instead of creating symlinks')
    p.add_argument('--force', action='store_true',
                   help='Replace existing non-symlink files')
    p.add_argument('--dest', default=None,
                   help='Override Inkscape extensions directory')
    p.add_argument('--skip-pip', action='store_true',
                   help='Do not attempt pip install -e .')
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    os.environ.setdefault('WEEDLINES_ROOT', str(ROOT))
    if not args.skip_pip and not args.dry_run and not args.uninstall:
        _try_editable_install()

    _ensure_src_path()
    from weedlines.install_ext import (
        format_report,
        inkscape_extensions_dir,
        install_extensions,
        uninstall_extensions,
    )

    dest = Path(args.dest) if args.dest else inkscape_extensions_dir()
    try:
        if args.uninstall:
            actions = uninstall_extensions(
                dest_dir=dest, dry_run=args.dry_run, root=ROOT)
        else:
            actions = install_extensions(
                dest_dir=dest,
                dry_run=args.dry_run,
                copy=args.copy,
                force=args.force,
                root=ROOT,
            )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(format_report(
        actions, dest, dry_run=args.dry_run, uninstall=args.uninstall))
    skipped = [a for a in actions if a[0].startswith('skip-')]
    if skipped and not args.uninstall:
        print(
            'Note: skipped {} existing path(s); re-run with --force to '
            'replace files.'.format(len(skipped)),
            file=sys.stderr,
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
