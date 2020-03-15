"""
Driver module for `vara-buildsetup`.
"""

import argparse
import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from varats.gui.buildsetup_window import BuildSetup
from varats.settings import get_value_or_default, CFG, save_config
from varats.vara_manager import setup_vara, BuildType


class VaRATSSetup:
    """
    Start VaRA-TS grafical user interface for setting up VaRA.
    """

    def __init__(self) -> None:
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)
        self.main_window = BuildSetup()

    def main(self) -> None:
        """
        Start VaRA setup GUI
        """
        sys.exit(self.app.exec_())


def update_term(text: str, enable_inline: bool = False) -> None:
    """
    Print/Update terminal text with/without producing new lines.

    Args:
        text: output text that should be printed
        enable_inline: print lines without new lines
    """
    text = text.replace(os.linesep, '').strip()
    if not text:
        return
    if enable_inline:
        _, columns = os.popen('/bin/stty size', 'r').read().split()
        print(text, end=(int(columns) - len(text) - 1) * ' ' + '\r', flush=True)
    else:
        print(text)


def parse_string_to_build_type(build_type: str) -> BuildType:
    """
    Convert a string into a BuildType

    Args:
        build_type: VaRA build configuration

    Test:
    >>> parse_string_to_build_type("DBG")
    <BuildType.DBG: 1>

    >>> parse_string_to_build_type("PGO")
    <BuildType.PGO: 4>

    >>> parse_string_to_build_type("DEV")
    <BuildType.DEV: 2>

    >>> parse_string_to_build_type("random string")
    <BuildType.DEV: 2>

    >>> parse_string_to_build_type("oPt")
    <BuildType.OPT: 3>

    >>> parse_string_to_build_type("OPT")
    <BuildType.OPT: 3>

    >>> parse_string_to_build_type("DEV-SAN")
    <BuildType.DEV_SAN: 5>
    """
    build_type = build_type.upper()
    if build_type == "DBG":
        return BuildType.DBG
    if build_type == "DEV":
        return BuildType.DEV
    if build_type == "OPT":
        return BuildType.OPT
    if build_type == "PGO":
        return BuildType.PGO
    if build_type == "DEV-SAN":
        return BuildType.DEV_SAN

    return BuildType.DEV


def main() -> None:
    """
    Build VaRA on cli.
    """
    llvm_src_dir = get_value_or_default(CFG, "llvm_source_dir",
                                        str(os.getcwd()) + "/vara-llvm/")
    llvm_install_dir = get_value_or_default(CFG, "llvm_install_dir",
                                            str(os.getcwd()) + "/VaRA/")

    parser = argparse.ArgumentParser("Build LLVM environment")

    parser.add_argument("-c",
                        "--config",
                        action="store_true",
                        default=False,
                        help="Only create a VaRA config file.")
    parser.add_argument("-i",
                        "--init",
                        action="store_true",
                        default=False,
                        help="Initializes VaRA and all components.")
    parser.add_argument("-u",
                        "--update",
                        action="store_true",
                        default=False,
                        help="Updates VaRA and all components.")
    parser.add_argument("-b",
                        "--build",
                        help="Builds VaRA and all components.",
                        action="store_true",
                        default=False)
    parser.add_argument("--version",
                        default=None,
                        nargs="?",
                        help="Version to download.")
    parser.add_argument("--buildtype",
                        default="dev",
                        choices=['dev', 'opt', 'pgo', 'dbg', 'dev-san'],
                        nargs="?",
                        help="Build type to use for LLVM and all subpackages.")
    parser.add_argument("llvmfolder",
                        help="Folder of LLVM. (Optional)",
                        nargs='?',
                        default=llvm_src_dir)
    parser.add_argument("installprefix",
                        default=llvm_install_dir,
                        nargs='?',
                        help="Folder to install LLVM. (Optional)")

    args = parser.parse_args()

    if not (args.config or args.init or args.update or args.build):
        parser.error(
            "At least one argument of --config, --init, --update or --build " +
            "must be given.")

    if args.config:
        save_config()
        return

    build_type = parse_string_to_build_type(args.buildtype)

    vara_version = args.version if args.version is not None else CFG['version']

    own_libgit2 = bool(CFG["own_libgit2"])
    include_phasar = bool(CFG["include_phasar"])

    setup_vara(args.init, args.update, args.build, Path(args.llvmfolder),
               args.installprefix, own_libgit2, include_phasar, vara_version,
               build_type, update_term)


if __name__ == '__main__':
    main()
