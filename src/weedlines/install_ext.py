#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install Weedlines Inkscape extension into the user extensions dir."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

WEED_FILES = (
    'weedlines.inx',
    'weedlines.py',
    'weedlines_dialog.py',
)


def repo_root() -> Path:
    """Checkout root that contains extensions/inkscape."""
    env = os.environ.get('WEEDLINES_ROOT')
    if env:
        root = Path(env).expanduser().resolve()
        if _has_sources(root):
            return root
    here = Path(__file__).resolve().parents[2]
    if _has_sources(here):
        return here
    # editable install: src/weedlines/install_ext.py → parents[2] is repo
    # site-packages layout: look beside package via importlib
    try:
        import weedlines as pkg
        pkg_root = Path(pkg.__file__).resolve().parent
        # installed wheel may ship extension data under package
        for cand in (pkg_root.parents[1], pkg_root.parents[2], Path.cwd()):
            if _has_sources(cand):
                return cand
    except Exception:
        pass
    raise FileNotFoundError(
        'Could not find extensions/inkscape for Weedlines. '
        'Set WEEDLINES_ROOT to the checkout, or run from the repo.'
    )


def _has_sources(root: Path) -> bool:
    return (root / 'extensions' / 'inkscape' / 'weedlines.inx').is_file()


def inkscape_extensions_dir() -> Path:
    """User Inkscape extensions directory (platform-appropriate)."""
    profile = os.environ.get('INKSCAPE_PROFILE_DIR')
    if profile:
        return Path(profile).expanduser().resolve() / 'extensions'
    if sys.platform == 'darwin':
        base = Path.home() / (
            'Library/Application Support/org.inkscape.Inkscape/'
            'config/inkscape'
        )
        return base / 'extensions'
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA') or str(Path.home())
        return Path(appdata) / 'inkscape' / 'extensions'
    xdg = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return Path(xdg) / 'inkscape' / 'extensions'


def source_map(root: Path | None = None) -> dict[str, Path]:
    root = root or repo_root()
    weed = root / 'extensions' / 'inkscape'
    return {name: weed / name for name in WEED_FILES}


def _same_target(dest: Path, source: Path) -> bool:
    try:
        return dest.resolve() == source.resolve() and dest.exists()
    except OSError:
        return False


def _link_or_copy(source: Path, dest: Path, copy: bool = False) -> str:
    if copy:
        shutil.copy2(source, dest)
        return 'copy'
    dest.symlink_to(source)
    return 'symlink'


def install_extensions(
    dest_dir: Path | None = None,
    dry_run: bool = False,
    copy: bool = False,
    force: bool = False,
    root: Path | None = None,
):
    """Symlink (or copy) weedlines extension files into dest_dir."""
    root = root or repo_root()
    dest_dir = Path(dest_dir) if dest_dir else inkscape_extensions_dir()
    mapping = source_map(root)
    missing = [str(p) for p in mapping.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            'Missing extension sources:\n  ' + '\n  '.join(missing)
        )

    actions = []
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    for name, source in sorted(mapping.items()):
        dest = dest_dir / name
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink() or dest.is_file():
                if _same_target(dest, source):
                    actions.append(('ok', dest, source))
                    continue
                if dest.is_symlink():
                    if dry_run:
                        actions.append(('replace-symlink', dest, source))
                    else:
                        dest.unlink()
                        kind = _link_or_copy(source, dest, copy=copy)
                        actions.append((kind, dest, source))
                    continue
                if not force:
                    actions.append(('skip-exists', dest, source))
                    continue
                if dry_run:
                    actions.append(('replace-file', dest, source))
                else:
                    dest.unlink()
                    kind = _link_or_copy(source, dest, copy=copy)
                    actions.append((kind, dest, source))
                continue
            actions.append(('skip-other', dest, source))
            continue

        if dry_run:
            actions.append(
                ('would-symlink' if not copy else 'would-copy', dest, source)
            )
        else:
            kind = _link_or_copy(source, dest, copy=copy)
            actions.append((kind, dest, source))
    return actions


def uninstall_extensions(
    dest_dir: Path | None = None,
    dry_run: bool = False,
    root: Path | None = None,
):
    root = root or repo_root()
    dest_dir = Path(dest_dir) if dest_dir else inkscape_extensions_dir()
    mapping = source_map(root)
    actions = []
    for name, source in sorted(mapping.items()):
        dest = dest_dir / name
        if not (dest.exists() or dest.is_symlink()):
            actions.append(('absent', dest, source))
            continue
        if dest.is_symlink():
            try:
                target = dest.resolve()
            except OSError:
                target = None
            if target and source.resolve() == target:
                if dry_run:
                    actions.append(('would-remove', dest, source))
                else:
                    dest.unlink()
                    actions.append(('removed', dest, source))
            else:
                actions.append(('skip-foreign-link', dest, source))
            continue
        if dest.is_file() and _same_target(dest, source):
            if dry_run:
                actions.append(('would-remove-copy', dest, source))
            else:
                dest.unlink()
                actions.append(('removed', dest, source))
            continue
        actions.append(('skip-other', dest, source))
    return actions


def format_report(actions, dest_dir, dry_run=False, uninstall=False) -> str:
    mode = 'uninstall' if uninstall else 'install'
    if dry_run:
        mode = 'dry-run ' + mode
    lines = [
        f'Weedlines Inkscape extension ({mode})',
        f'Destination: {dest_dir}',
    ]
    for action, dest, source in actions:
        lines.append(f'  [{action:<18}] {dest} -> {source}')
    if not uninstall:
        lines.append('Restart Inkscape to reload extensions.')
    return '\n'.join(lines)
