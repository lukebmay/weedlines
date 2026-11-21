# Cache home

**Status:** done

## Goal

`cache_dir` honors `WEEDLINES_CACHE_HOME` on every
call. A set value is the cache directory, with no
`weedlines` suffix. An unset value keeps the paths
that function already returns. The runtime part is
not edited.

## Do

Edit `cache_dir` in
`extensions/inkscape/weedlines_job.py`. That
function is the cache resolver. Read the
environment inside the function on every call. Do
not store the directory on the module. Do not
resolve it once per process.

When `WEEDLINES_CACHE_HOME` is non-empty, that
value is the directory on every platform. Do not
append `weedlines`. It wins over `XDG_CACHE_HOME`
and over the platform directory.

When `WEEDLINES_CACHE_HOME` is unset or empty,
leave the branch the function already uses. A set
`XDG_CACHE_HOME` is that directory plus
`weedlines`, including on Windows and macOS.
Otherwise Linux is `~/.cache/weedlines`, Windows
is `%LOCALAPPDATA%\weedlines\cache`, and macOS is
`~/Library/Caches/weedlines`. Keep the existing
fallback when `LOCALAPPDATA` is unset.

`XDG_CACHE_HOME` is read only in `cache_dir`. Do
not add another reader. Do not change
`src/weedlines/install_ext.py`. Its
`XDG_CONFIG_HOME` read is Inkscape's extensions
directory, not a weedlines home.

Do not add a config, data, state, or runtime
home. Do not record data or state at install. Do
not move the Inkscape extensions directory.

Do not edit the guide. That includes
`agents/architecture/runtime.md`,
`agents/architecture/install.md`,
`agents/architecture.md`, `agents/project.md`,
`agents/acceptance.md`, and the product README.
The human has not answered the runtime sentence.

Callers already ask `cache_dir` when they need a
path, including the result files, the ready file,
the job file, and `host.log`. Leave that. Do not
snapshot the directory at import. Do not edit
`weedlines_ready.py` or `weedlines_svg.py`.

## Checks

Add `tests/test_job_cache.py`. Load `weedlines_job`
the way `tests/test_job_records.py` does. Point
every resolved directory at a temp path, including
the home used when the variable is unset. Do not
write the real cache. Add one line for the new
file in `tests/README.md`.

- A non-empty `WEEDLINES_CACHE_HOME` is the
  directory on Linux, Windows, and macOS. The
  path has no added `weedlines` suffix. It still
  wins when `XDG_CACHE_HOME` is set.
- With `WEEDLINES_CACHE_HOME` unset, a set
  `XDG_CACHE_HOME` is that directory plus
  `weedlines` on Linux, Windows, and macOS.
  With both unset, Linux is `~/.cache/weedlines`,
  Windows is `%LOCALAPPDATA%\weedlines\cache`,
  and macOS is `~/Library/Caches/weedlines`.
- Two calls in one process, after the environment
  changes, return the new directory.
- A search of the product code shows
  `XDG_CACHE_HOME` only inside `cache_dir`.
- `inkscape_extensions_dir` in
  `src/weedlines/install_ext.py` is unchanged.
- No install record for data or state, and no
  runtime home.
- No guide file is edited.

## Note

`cache_dir` in `extensions/inkscape/weedlines_job.py`
reads `WEEDLINES_CACHE_HOME` on every call. A
non-empty value is the directory, with no
`weedlines` suffix, and it wins over
`XDG_CACHE_HOME` on Linux, Windows, and macOS.
Unset or empty leaves the branch already there:
`XDG_CACHE_HOME/weedlines` on those platforms,
else `~/.cache/weedlines`,
`%LOCALAPPDATA%\weedlines\cache` (or
`~/weedlines/cache` when `LOCALAPPDATA` is unset),
and `~/Library/Caches/weedlines`. The directory is
not stored on the module. Callers are unchanged.
`weedlines_ready.py`, `weedlines_svg.py`, and
`src/weedlines/install_ext.py` were not edited.
No config, data, state, or runtime home was added.
The guide was not edited.

Why: the resolver never read the app cache
variable, so a set `WEEDLINES_CACHE_HOME` could
not name the directory.

Checked with `python3 -m pytest tests/test_job_cache.py`:
14 passed in 0.02s. Every resolved directory is
under the test temp path, including the home used
when the variable is unset. A search of the
product `*.py` files finds `XDG_CACHE_HOME` only
inside `cache_dir`. `inkscape_extensions_dir` is
untouched. No guide file is in this diff.

Summary: No defect in this change. `cache_dir` reads
`WEEDLINES_CACHE_HOME` inside the function on every
call. A non-empty value is the directory, with no
`weedlines` suffix, and it wins over
`XDG_CACHE_HOME` on Linux, Windows, and macOS.
Unset or empty keeps the old branch, including
`~/weedlines/cache` when `LOCALAPPDATA` is unset.
The directory is not stored on the module. Callers
are unchanged. No config, data, state, or runtime
home was added. The guide was not edited.

Context worth keeping: The environment is read
inside `cache_dir` on every call. Product Python
reads `XDG_CACHE_HOME` only there.
`inkscape_extensions_dir` still resolves Inkscape's
extensions directory and was not edited. The
runtime sentence still does not name
`WEEDLINES_CACHE_HOME`. That wait stays until the
human answers. It is not a defect in this change.
`extensions/inkscape/` has more than one source
file and no directory index. `weedlines_dialog/README.md`
indexes only that subdirectory. The check is
`agents/handbook.md`, Source files. That debt is
outside this change. It was not fixed, and no plan
was filed. The pass is `cr-01.md`.

Result: No defect. `python3 -m pytest
tests/test_job_cache.py`: 14 passed in 0.02s.
PyQt6 6.7.1. No Inkscape. The search checks have
no test. They were confirmed by search and by the
diff. The missing directory index is debt outside
the change.
