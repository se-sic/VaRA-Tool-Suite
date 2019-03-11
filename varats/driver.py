#!/usr/bin/env python3
"""
Main drivers for VaRA-TS
"""

import os
import sys
import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


from varats import settings
from varats.settings import get_value_or_default, CFG
from varats.gui.main_window import MainWindow
from varats.gui.buildsetup_window import BuildSetup
from varats.vara_manager import setup_vara, BuildType
from varats.tools.commit_map import generate_commit_map

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


def update_term(text, multiline=False):
    if not multiline:
        text = text.replace(os.linesep, ' ')
        _, columns = os.popen('stty size', 'r').read().split()
        print(text, end=(int(columns) - len(text) - 1) * ' ' + '\r',
              flush=True)
    else:
        print(text)


def build_setup():
    """
    Build VaRA on cli.
    """
    llvm_src_dir = get_value_or_default(CFG, "llvm_source_dir",
                                        str(os.getcwd()) + "/vara-llvm/")
    llvm_install_dir = get_value_or_default(CFG, "llvm_install_dir",
                                            str(os.getcwd()) + "/VaRA/")

    parser = argparse.ArgumentParser("Build LLVM environment")

    parser.add_argument("-i", "--init", action="store_true", default=False,
                        help="Initializes VaRA and all components.")
    parser.add_argument("-u", "--update", action="store_true", default=False,
                        help="Updates VaRA and all components.")
    parser.add_argument("-b", "--build",
                        help="Builds VaRA and all components.",
                        action="store_true", default=False)
    parser.add_argument("--version", default=None, nargs="?",
                        help="Version to download.")
    parser.add_argument("--buildtype", default="dev", nargs="?",
                        help="Build type to use for LLVM and all subpackages.")
    parser.add_argument("llvmfolder", help="Folder of LLVM. (Optional)",
                        nargs='?', default=llvm_src_dir)
    parser.add_argument("installprefix", default=llvm_install_dir, nargs='?',
                        help="Folder to install LLVM. (Optional)")

    args = parser.parse_args()

    build_type = parse_string_to_build_type(args.buildtype)

    if not (args.init or args.update or args.build):
        parser.error("At least one argument of --init, --update or --build " +
                     "must be given.")

    vara_version = args.version if args.version is not None else CFG['version']

    setup_vara(args.init, args.update, args.build, args.llvmfolder,
               args.installprefix, vara_version, build_type, update_term)


def parse_string_to_build_type(build_type: str) -> BuildType:
    """
    Convert a string into a BuildType

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

    return BuildType.DEV


def gen_fosd_graph():
    from varats.settings import CFG
    from varats.jupyterhelper.file import load_commit_report

    from pathlib import Path

    reports = []
    result_dir = Path("/home/vulder/vara/fosd_results/")
    for file_path in result_dir.iterdir():
        if file_path.stem.startswith("gzip"):
            print("Loading file: ", file_path)
            reports.append(load_commit_report(file_path))
    # Sort with commit map
    commits = []
    interactions = []
    head_interactions = []

    for report in reports:
            commits.append(report.head_commit)
            interactions.append(report.number_of_df_interactions())
            hi = report.number_of_head_df_interactions()
            head_interactions.append(hi[0] + hi[1])

    df=pd.DataFrame({'x': commits, 'Interactions': interactions,
                     "HEAD Interactions": head_interactions})
    plt.plot('x', 'Interactions', data=df, color='red')
    plt.plot('x', 'HEAD Interactions', data=df, color='green')
    plt.show()


def gen_fosd_example():
    df = pd.DataFrame(
            {'20540be': [25, 0, 0],
             '8aa53f1': [0, 4, 5],
             'a604573': [0, 0, 0],
             'e48a916': [0, 0, 0],
             '8ebed06': [17, 14, 0],
             'd2e7cf9': [0, 0, 0],
             '63aa226': [0, 30, 6]})

    sns.set(font_scale=1.4)
    sns.heatmap(df, cmap=sns.color_palette("Reds", n_colors=30),
                xticklabels=["20540be",
                             "8aa53f1",
                             "a604573",
                             "e48a916",
                             "8ebed06",
                             "d2e7cf9",
                             "63aa226"],
                yticklabels=["Foo",
                             "Bar",
                             "Bazz"],
                vmin=0, vmax=30,
                linewidth=1,
                linecolor="black",
                cbar_kws={'label': "Interactions"})

    plt.show()


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
