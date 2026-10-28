# Install

When to use: Installing or updating the Inkscape extension.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The CLI owns the links into Inkscape's extensions directory. It
does not own the solvers, the window, or the figure check.

`weedlines install` symlinks `extensions/inkscape/` into the user
extensions directory. `--copy` copies instead. An existing symlink
that already points at this source is left alone. A symlink that
points elsewhere is replaced. A real file is skipped unless
`--force`. `--dry-run` prints and writes nothing. `--uninstall`
removes only destinations that resolve to this checkout.

The destination is `--dest`, else `$INKSCAPE_PROFILE_DIR/extensions`,
else the platform Inkscape config `extensions` folder. On Linux
that is `$XDG_CONFIG_HOME/inkscape/extensions` or
`~/.config/inkscape/extensions`. The checkout is `$WEEDLINES_ROOT`
when that tree contains `extensions/inkscape/weedlines.inx`.
Otherwise it is the repo that contains the package. The extension
files are not inside the installed wheel. A tree without those
sources fails the install instead of inventing them.

`weedlines update` installs the current tree when this is not a
git checkout, or when `git status --porcelain` is non-empty. It
does not pull in those cases. A clean checkout runs
`git pull --ff-only` and, on failure, stops without installing.
`--dry-run` neither pulls nor writes links.

`./install` sets `WEEDLINES_ROOT` to the checkout and, unless
`--skip-pip`, `--dry-run`, or `--uninstall`, runs `pip install -e .`
when `import weedlib` fails. The `weedlines` console script does
not run pip. Restart Inkscape after a real install so it reloads
the extension.

Symlinks are the default so a later pull is what Inkscape loads.
