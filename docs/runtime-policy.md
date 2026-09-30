# Runtime support policy

Status: active
Last reviewed: 2026-09-30

## Supported runtime

Borderless Jobs supports CPython 3.12.x. The repository-level
[`.python-version`](../.python-version) selects that minor release; environments should
resolve the latest available security-patched 3.12 release rather than relying on a
specific patch version.

The verified development platform is:

- Ubuntu 24.04 LTS on x86-64;
- CPython 3.12;
- `uv` for Python installation and environment management.

Ubuntu is the only platform claimed as verified. Docker is the portability path.
macOS, Windows, other Linux distributions, architectures, and Python implementations
remain best-effort until their full setup and test workflows run in CI or on maintained
hardware.

## Why Python 3.12

- Python 3.12 receives upstream security support through October 2028.
- It is already available on the verified Ubuntu development machine.
- Laya requires Python 3.10 or newer and its documented `uv` setup uses Python 3.12.
- Selecting one conservative minor version reduces lockfile and native-wheel variance
  across local development, CI, database tooling, and optional model runtimes.

The project will review this choice before Python 3.12 reaches end of life, or earlier
when a required dependency withdraws support or a newer minor provides a measured
benefit without reducing compatibility.

## Verification

Run the repository check from its root:

```bash
./scripts/check-python-version.sh
```

Pass an explicit interpreter when diagnosing a machine with several installations:

```bash
./scripts/check-python-version.sh /path/to/python
```

The check exits successfully only for CPython 3.12.x. Failure output states the detected
version or missing executable and provides the corresponding `uv python install 3.12`
remediation.

## Sources

- [CPython supported versions](https://devguide.python.org/versions/)
- [Laya installation requirements](https://github.com/NandhaKishorM/laya#installation)
