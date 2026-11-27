"""Shared, dependency-free interpreter/platform preflight for the shell scripts."""
import os
from pathlib import Path
import platform
import struct
import sys
import sysconfig


def check(mode, project):
    version = platform.python_version()
    if (sys.implementation.name != 'cpython'
            or sys.version_info[:2] not in ((3, 11), (3, 12), (3, 13))
            or sysconfig.get_config_var('Py_GIL_DISABLED')):
        raise RuntimeError(
            'Gefunden: {} {}. Benötigt: reguläres CPython 3.11–3.13 '
            '(empfohlen: 3.12); paddlepaddle==3.2.2 unterstützt Python 3.14 nicht.'
            .format(sys.implementation.name, version))
    machine = platform.machine().lower()
    if sys.platform != 'linux' or struct.calcsize('P') != 8 or machine not in ('x86_64', 'aarch64'):
        raise RuntimeError('Benötigt: 64-Bit-Linux auf x86_64 oder aarch64; gefunden: '
                           '{} / {}.'.format(sys.platform, machine))
    # Match the PySide6 6.11.1 Linux wheels, not merely the Python version.
    minimum = (2, 34) if machine == 'x86_64' else (2, 39)
    try:
        libc = os.confstr('CS_GNU_LIBC_VERSION') or ''
        libc_version = tuple(int(x) for x in libc.split()[-1].split('.')[:2])
    except (ValueError, OSError, IndexError):
        libc, libc_version = 'unbekannt/musl', ()
    if not libc.startswith('glibc ') or libc_version < minimum:
        raise RuntimeError('Benötigt: glibc >= {}.{} auf {}; gefunden: {}. '
                           'Alpine/musl wird mit diesen Binärpaketen nicht unterstützt.'
                           .format(*minimum, machine, libc))
    if mode == 'venv':
        expected = Path(project) / 'venv'
        if (sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected.resolve()
                or not (expected / 'pyvenv.cfg').is_file()):
            raise RuntimeError('Der Interpreter gehört nicht zur Projektumgebung venv.')
    else:
        if sys.prefix != sys.base_prefix:
            raise RuntimeError('Eine fremde virtuelle Umgebung wird nicht als Basis verwendet.')
        import venv  # noqa: F401
        import ensurepip  # noqa: F401
    print(version)


if __name__ == '__main__':
    try:
        check(sys.argv[1], sys.argv[2])
    except (RuntimeError, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
