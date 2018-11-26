#!/usr/bin/env python3
"""
Main drivers for VaRA-TS
"""

import os
import sys
import argparse

from varats import settings
from varats.settings import get_value_or_default, CFG
from varats.gui.main_window import MainWindow
from varats.gui.buildsetup_window import BuildSetup
from varats.vara_manager import setup_vara
from varats.tools.commitmap import generate_commit_map

from PyQt5.QtWidgets import QApplication, QMessageBox


class VaRATSGui:

    def __init__(self):
        self.app = QApplication(sys.argv)

        if settings.CFG["config_file"].value is None:
            err = QMessageBox()
            err.setIcon(QMessageBox.Warning)
            err.setWindowTitle("Missing config file.")
            err.setText("Could not find VaRA config file.\n"
                        "Should we create a config file in the current folder?")
            err.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            answer = err.exec_()
            if answer == QMessageBox.Yes:
                settings.save_config()
            else:
                sys.exit()

        self.main_window = MainWindow()

    def main(self):
        """Setup and Run Qt application"""
        sys.exit(self.app.exec_())


class VaRATSSetup:

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = BuildSetup()

    def main(self):
        sys.exit(self.app.exec_())


def main_graph_view():
    """
    Start VaRA-TS driver and run application.
    """
    driver = VaRATSGui()
    driver.main()


def update_term(text):
    text.rstrip('\r\n').replace('\n', ' ')  # TODO: test with 'repr(text)'
    print(text, end='\r', flush=True)


def build_setup():
    """
    Build VaRA on terminal.
    """
    llvm_src_dir = get_value_or_default(CFG, "llvm_source_dir",
                                        str(os.getcwd()) + "/vara-llvm/")
    llvm_install_dir = get_value_or_default(CFG, "llvm_install_dir",
                                            str(os.getcwd()) + "/VaRA/")

    parser = argparse.ArgumentParser("Build LLVM environment")
    parser.add_argument("--init", help="Initializes VaRA and all components.",
                        const=True, nargs='?')
    parser.add_argument("--update", help="Updates VaRA and all components.",
                        const=True, nargs='?')
    parser.add_argument("--build", help="Builds VaRA and all components.",
                        const=True, nargs='?')
    parser.add_argument("--branch", default=None, nargs="?",
                        help="Branch name to download.")
    parser.add_argument("llvmfolder", help="Folder of LLVM. (Optional)",
                        nargs='?', default=llvm_src_dir)
    parser.add_argument("installprefix",
                        help="Folder to install LLVM. (Optional)", nargs='?',
                        default=llvm_install_dir)

    args = parser.parse_args()

    setup_vara(args.init, args.update, args.build, args.llvmfolder,
               args.branch, args.installprefix, update_term)


def main_gen_commitmap():
    """
    Create a commit map for a repository.
    """
    parser = argparse.ArgumentParser("Commit map creator")
    parser.add_argument("path", help="Path to git repository")
    parser.add_argument("-o", "--output", help="Output filename",
                        default="c_map")
    parser.add_argument("--end", help="End of the commit range (inclusive)",
                        default="HEAD")
    parser.add_argument("--start",
                        help="Start of the commit range (exclusive)",
                        default=None)

    args = parser.parse_args()

    generate_commit_map(args.path, args.output, args.end, args.start)


if __name__ == "__main__":
    main()
