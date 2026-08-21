#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weedlines command-line interface."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

__version__ = '0.1.0'


def _print_status(msg: str, stream=None) -> None:
    stream = stream or sys.stderr
    stream.write(msg.rstrip() + '\n')


def cmd_install(args: argparse.Namespace) -> int:
    from .install_ext import (
        format_report,
        inkscape_extensions_dir,
        install_extensions,
        uninstall_extensions,
    )

    dest = Path(args.dest) if args.dest else inkscape_extensions_dir()
    try:
        if args.uninstall:
            actions = uninstall_extensions(
                dest_dir=dest, dry_run=args.dry_run)
        else:
            actions = install_extensions(
                dest_dir=dest,
                dry_run=args.dry_run,
                copy=args.copy,
                force=args.force,
            )
    except FileNotFoundError as exc:
        _print_status(str(exc))
        return 1
    print(format_report(
        actions, dest, dry_run=args.dry_run, uninstall=args.uninstall))
    skipped = [a for a in actions if a[0].startswith('skip-')]
    if skipped and not args.uninstall:
        _print_status(
            f'Note: skipped {len(skipped)} existing path(s); '
            're-run with --force to replace files.'
        )
    return 0


def _git_root() -> Path | None:
    try:
        out = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return Path(out) if out else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_dirty(root: Path) -> bool:
    try:
        out = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=str(root),
            text=True,
        )
        return bool(out.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True


def cmd_update(args: argparse.Namespace) -> int:
    """Pull (if clean) then reinstall the Inkscape extension."""
    root = _git_root()
    if root is None:
        _print_status('Not a git checkout; installing current tree only.')
        return cmd_install(args)

    dirty = _git_dirty(root)
    if dirty:
        _print_status(
            'Working tree is dirty — skipping git pull; '
            'installing local tree.'
        )
    else:
        _print_status('Pulling latest…')
        if not args.dry_run:
            try:
                subprocess.check_call(['git', 'pull', '--ff-only'], cwd=str(root))
            except subprocess.CalledProcessError:
                _print_status('git pull --ff-only failed.', sys.stderr)
                return 1
        else:
            _print_status('(dry-run) would run: git pull --ff-only')

    _print_status('Installing extension…')
    return cmd_install(args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='weedlines',
        description='Weedlines — Inkscape weed-cut algorithms and tools.',
    )
    p.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    sub = p.add_subparsers(dest='command', required=True)

    inst = sub.add_parser(
        'install',
        help='Install/update the Inkscape extension (idempotent)',
    )
    inst.add_argument('--dry-run', action='store_true')
    inst.add_argument('--uninstall', action='store_true')
    inst.add_argument('--copy', action='store_true',
                      help='Copy files instead of symlinks')
    inst.add_argument('--force', action='store_true',
                      help='Replace existing non-symlink files')
    inst.add_argument('--dest', default=None,
                      help='Override Inkscape extensions directory')
    inst.set_defaults(func=cmd_install)

    upd = sub.add_parser(
        'update',
        help='git pull (if clean) then install; dirty tree installs as-is',
    )
    upd.add_argument('--dry-run', action='store_true')
    upd.add_argument('--copy', action='store_true')
    upd.add_argument('--force', action='store_true')
    upd.add_argument('--dest', default=None)
    upd.add_argument('--uninstall', action='store_true', help=argparse.SUPPRESS)
    upd.set_defaults(func=cmd_update)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == '__main__':
    raise SystemExit(main())
