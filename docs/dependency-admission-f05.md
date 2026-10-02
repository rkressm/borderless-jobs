# F05 development-tool admission (2026-10-02)

Scope: `dev` group only. These tools are consumed by `scripts/check-quality.sh`; no
runtime dependency is admitted. The Python standard library offers `unittest` and
`trace` but does not provide comparable formatting, linting, strict static typing,
pytest-style fixtures, or branch-coverage reporting as one maintainable quality loop.

| Direct package | Purpose and alternative | Maintainer, provenance, license, security |
| --- | --- | --- |
| `ruff==0.16.9` | Format and lint; replaces separate formatter, import sorter, and lint plugins. | [Astral repository](https://github.com/astral-sh/ruff), [PyPI release](https://pypi.org/project/ruff/0.16.9/), MIT; [advisories](https://github.com/astral-sh/ruff/security/advisories) checked 2026-10-02: none published. |
| `mypy==2.3.1` | Strict static typing; stdlib annotations do not check themselves. | [Python/mypy repository](https://github.com/python/mypy), [PyPI release](https://pypi.org/project/mypy/2.3.1/), MIT; [advisories](https://github.com/python/mypy/security/advisories) checked 2026-10-02: none published. |
| `pytest==9.1.1` | Focused test runner, including existing `unittest` tests; `unittest` alone lacks the planned fixture ergonomics. | [pytest-dev repository](https://github.com/pytest-dev/pytest), [PyPI release](https://pypi.org/project/pytest/9.1.1/), MIT; [advisories](https://github.com/pytest-dev/pytest/security/advisories) checked 2026-10-02: none published. |
| `coverage==7.16.2` | Branch-coverage measurement; stdlib `trace` lacks this reporting. Avoids a `pytest-cov` plugin. | [coveragepy repository](https://github.com/coveragepy/coveragepy), [PyPI release](https://pypi.org/project/coverage/7.16.2/), Apache-2.0; [advisories](https://github.com/coveragepy/coveragepy/security/advisories) checked 2026-10-02: none published. |

All four publishers show ongoing releases in 2026. Packages are resolved only from
the configured default PyPI index under `first-index` with TLS; `uv.lock` records
artifact hashes. No VCS, archive URL, or new build backend is added. Installation
executes third-party code only in the development environment; test collection must
continue to use reviewed repository tests and plugins. This is not a security audit of
every transitive package.

Transitive review: the eight local packages remain dependency-free at runtime. The
dev-only graph adds `iniconfig`, `packaging`, `pluggy`, and `pygments` below pytest
(plus `colorama` in the cross-platform lockfile for Windows);
`ast-serialize`, `librt`, `mypy-extensions`, `pathspec`, and `typing-extensions` below
mypy. Ruff and coverage add no transitive packages. Ruff contains a Rust binary;
mypy and coverage have compiled wheel components. The Linux install selected wheels,
not source builds. No package adds an application runtime import or installer hook in
the project manifest.

Decision: accept for F05, reviewed 2026-10-02. `uv lock --check --offline`,
`uv tree --locked --all-groups --offline`, and locked all-package sync passed;
format, lint, strict type, pytest, and branch-coverage checks passed. Temporary
format, type, and test failures each caused the corresponding command to fail and
were removed. Residual risk: published advisory lists and hashes cannot rule out an
undisclosed compromised upstream release; future updates require the same review.
