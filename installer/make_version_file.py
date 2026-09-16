# -*- coding: utf-8 -*-
"""
make_version_file.py — номер версии приложения в одном месте.

Единственный источник правды — строка VERSION в ies-generator/ies_app.py
(сейчас это «1.2»). Скрипт приводит её к виду «1.2.0» и умеет:

  * напечатать нормализованную версию (--print-version) — её забирает
    GitHub Actions и передаёт в Inno Setup;
  * записать файл ресурса версии для PyInstaller (--out), чтобы в
    свойствах готового IES_Generator.exe были видны название, издатель
    и номер версии.

Чтобы поднять версию, достаточно поменять VERSION в ies_app.py —
и .exe, и установщик подхватят новое значение автоматически.
"""

import argparse
import os
import re
import sys

COMPANY = "ASTZ"
PRODUCT = "IES Generator"
DESCRIPTION = "IES Generator - photometric file tool"
EXE_NAME = "IES_Generator.exe"

TEMPLATE = """\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=%(tuple)s,
    prodvers=%(tuple)s,
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', '%(company)s'),
         StringStruct('FileDescription', '%(description)s'),
         StringStruct('FileVersion', '%(version)s'),
         StringStruct('InternalName', '%(product)s'),
         StringStruct('LegalCopyright', '%(company)s'),
         StringStruct('OriginalFilename', '%(exe)s'),
         StringStruct('ProductName', '%(product)s'),
         StringStruct('ProductVersion', '%(version)s')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def read_version(app_path):
    """Достать VERSION из ies_app.py и привести к виду X.Y.Z."""
    with open(app_path, encoding="utf-8") as f:
        source = f.read()

    match = re.search(r"^VERSION\s*=\s*[\"']([^\"']+)[\"']", source, re.MULTILINE)
    if not match:
        raise SystemExit("В файле %s не найдена строка VERSION = \"...\"" % app_path)

    parts = [p for p in match.group(1).strip().split(".") if p != ""]
    if not all(p.isdigit() for p in parts):
        raise SystemExit("VERSION = %r — ожидались только цифры и точки"
                         % match.group(1))

    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:3])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_app = os.path.join(os.path.dirname(here), "ies-generator", "ies_app.py")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", default=default_app,
                        help="путь к ies_app.py")
    parser.add_argument("--out",
                        help="куда записать файл ресурса версии для PyInstaller")
    parser.add_argument("--print-version", action="store_true",
                        help="напечатать нормализованную версию (например 1.2.0)")
    args = parser.parse_args()

    version = read_version(args.app)

    if args.out:
        numbers = version.split(".") + ["0"]
        version_tuple = "(%s)" % ", ".join(numbers[:4])
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(TEMPLATE % {
                "tuple": version_tuple,
                "version": version,
                "company": COMPANY,
                "product": PRODUCT,
                "description": DESCRIPTION,
                "exe": EXE_NAME,
            })
        if not args.print_version:
            print("Файл версии записан: %s (версия %s)" % (args.out, version))

    if args.print_version:
        sys.stdout.write(version)


if __name__ == "__main__":
    main()
