#!/usr/bin/env python3
"""
Main drivers for VaRA-TS
"""

import os
import sys
import argparse
from pathlib import Path
from argparse_utils import enum_action

import varats.development as dev
from varats import settings
from varats.settings import get_value_or_default,\
    CFG, generate_benchbuild_config, save_config
from varats.gui.main_window import MainWindow
from varats.gui.buildsetup_window import BuildSetup
from varats.vara_manager import setup_vara, BuildType, LLVMProjects
from varats.tools.commit_map import generate_commit_map, store_commit_map
from varats.plots.plots import extend_parser_with_plot_args, build_plot
from varats.utils.cli_util import cli_yn_choice
from varats.paper.case_study import SamplingMethod, generate_case_study,\
    store_case_study
import varats.paper.paper_config_manager as PCM

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt


class VaRATSGui:
    """
    Start VaRA-TS grafical user interface for graphs.
    """

    def __init__(self):
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)

        if settings.CFG["config_file"].value is None:
            err = QMessageBox()
            err.setIcon(QMessageBox.Warning)
            err.setWindowTitle("Missing config file.")
            err.setText(
                "Could not find VaRA config file.\n"
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
    """
    Start VaRA-TS grafical user interface for setting up VaRA.
    """

    def __init__(self):
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)
        self.main_window = BuildSetup()

    def main(self):
        """
        Start VaRA setup GUI
        """
        sys.exit(self.app.exec_())


def main_graph_view():
    """
    Start VaRA-TS driver and run application.
    """
    driver = VaRATSGui()
    driver.main()


def update_term(text):
    """
    Print/Update terminal text without producing new lines.
    """
    text = text.replace(os.linesep, ' ')
    _, columns = os.popen('/bin/stty size', 'r').read().split()
    print(text, end=(int(columns) - len(text) - 1) * ' ' + '\r', flush=True)


def build_setup():
    """
    Build VaRA on cli.
    """
    llvm_src_dir = get_value_or_default(CFG, "llvm_source_dir",
                                        str(os.getcwd()) + "/vara-llvm/")
    llvm_install_dir = get_value_or_default(CFG, "llvm_install_dir",
                                            str(os.getcwd()) + "/VaRA/")

    parser = argparse.ArgumentParser("Build LLVM environment")

    parser.add_argument(
        "-c",
        "--config",
        action="store_true",
        default=False,
        help="Only create a VaRA config file.")
    parser.add_argument(
        "-i",
        "--init",
        action="store_true",
        default=False,
        help="Initializes VaRA and all components.")
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        default=False,
        help="Updates VaRA and all components.")
    parser.add_argument(
        "-b",
        "--build",
        help="Builds VaRA and all components.",
        action="store_true",
        default=False)
    parser.add_argument(
        "--version", default=None, nargs="?", help="Version to download.")
    parser.add_argument(
        "--buildtype",
        default="dev",
        nargs="?",
        help="Build type to use for LLVM and all subpackages.")
    parser.add_argument(
        "llvmfolder",
        help="Folder of LLVM. (Optional)",
        nargs='?',
        default=llvm_src_dir)
    parser.add_argument(
        "installprefix",
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

    setup_vara(args.init, args.update, args.build, args.llvmfolder,
               args.installprefix, own_libgit2, vara_version, build_type,
               update_term)


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


def main_gen_graph():
    """
    Main function for the graph generator.

    `vara-gen-graph`
    """
    parser = argparse.ArgumentParser("VaRA graph generator")
    parser.add_argument(
        "-r", "--result-folder", help="Folder with result files")
    parser.add_argument("-p", "--project", help="Project name")
    parser.add_argument("-c", "--cmap", help="Path to commit map")
    parser.add_argument("-g", "--graph", help="Graph type")
    parser.add_argument(
        "-v",
        "--view",
        help="Show the plot instead of saving it",
        action='store_true',
        default=False)

    extend_parser_with_plot_args(parser)

    args = {
        k: v
        for k, v in vars(parser.parse_args()).items() if v is not None
    }

    build_plot(**args)


def main_gen_benchbuild_config():
    """
    Main function for the benchbuild config creator.

    `vara-gen-bbconfig`
    """
    parser = argparse.ArgumentParser("Benchbuild config generator.")
    parser.add_argument("--bb-root",
                        help="Set an alternative BenchBuild root folder.")
    if settings.CFG["config_file"].value is None:
        if cli_yn_choice("Error! No VaRA config found. Should we create one?"):
            save_config()
        else:
            sys.exit()

    args = parser.parse_args()
    if args.bb_root is not None:
        if os.path.isabs(str(args.bb_root)):
            bb_root_path = str(args.bb_root)
        else:
            bb_root_path = os.path.dirname(str(CFG["config_file"])) +\
                "/" + str(args.bb_root)

        print("Setting BB path to: ", bb_root_path)
        CFG["benchbuild_root"] = bb_root_path
        save_config()

    if CFG["benchbuild_root"].value is None:
        CFG["benchbuild_root"] = os.path.dirname(str(CFG["config_file"]))\
                                                 + "/benchbuild"
        print("Setting BB path to: ", CFG["benchbuild_root"])
        save_config()

    generate_benchbuild_config(CFG, str(CFG["benchbuild_root"]) +
                               "/.benchbuild.yml")


def main_gen_commitmap():
    """
    Create a commit map for a repository.
    """
    parser = argparse.ArgumentParser("vara-gen-commitmap")
    parser.add_argument("path", help="Path to git repository")
    parser.add_argument(
        "--end", help="End of the commit range (inclusive)", default="HEAD")
    parser.add_argument(
        "--start", help="Start of the commit range (exclusive)", default=None)
    parser.add_argument("-o", "--output", help="Output filename")

    args = parser.parse_args()

    if args.path.endswith(".git"):
        path = Path(args.path[:-4])
    else:
        path = Path(args.path)

    if not path.exists():
        raise argparse.ArgumentTypeError("Repository path does not exist")

    cmap = generate_commit_map(path, args.end, args.start)

    if args.output is None:
        output_name = "{result_folder}/{project_name}/{file_name}.cmap"\
            .format(
                result_folder=CFG["result_dir"],
                project_name=path.name.replace("-HEAD", ""),
                file_name=path.name.replace("-HEAD", ""))
    else:
        if args.output.endswith(".cmap"):
            output_name = args.output
        else:
            output_name = args.output + ".cmap"
    store_commit_map(cmap, output_name)


def main_casestudy():
    """
    Allow easier management of case studies
    """
    parser = argparse.ArgumentParser("VaRA case-study manager")
    sub_parsers = parser.add_subparsers(help="Subcommand", dest="subcommand")

    status_parser = sub_parsers.add_parser(
        'status', help="Show status of current case study")
    status_parser.add_argument(
        "--filter-regex",
        help="Provide a regex to filter the shown case studies",
        type=str,
        default=".*")
    status_parser.add_argument(
        "--paper_config",
        help="Use this paper config instead of the configured one",
        default=None)
    status_parser.add_argument(
        "-s",
        "--short",
        help="Only print a short summary",
        action="store_true",
        default=False)
    status_parser.add_argument(
        "--list-revs",
        help="Print a list of revisions for every stage and every case study",
        action="store_true",
        default=False)

    gen_parser = sub_parsers.add_parser('gen', help="Generate a case study.")
    gen_parser.add_argument(
        "paper_config_path",
        help="Path to paper_config folder (e.g., paper_configs/ase-17)")
    gen_parser.add_argument("git_path", help="Path to git repository")
    parser.add_argument(
        "--end", help="End of the commit range (inclusive)", default="HEAD")
    parser.add_argument(
        "--start", help="Start of the commit range (exclusive)", default=None)

    gen_parser.add_argument("distribution", action=enum_action(SamplingMethod))
    gen_parser.add_argument(
        "--num-rev",
        type=int,
        default=10,
        help="Number of revisions to select.")
    gen_parser.add_argument(
        "-v", "--version", type=int, default=0, help="Case study version.")
    gen_parser.add_argument(
        "--extra-revs",
        nargs="+",
        default=[],
        help="Add a list of additional revisions to the case-study")

    ext_parser = sub_parsers.add_parser('ext', help="Extend a case study.")
    ext_parser.add_argument("stratigy", action=enum_action(SamplingMethod))

    args = {
        k: v
        for k, v in vars(parser.parse_args()).items() if v is not None
    }

    if args['subcommand'] == 'status':
        if 'paper_config' in args:
            CFG['paper_config']['current_config'] = args['paper_config']

        if args['short'] and args['list_revs']:
            parser.error(
                "At least one argument of: --short, --list-revs can be used.")

        PCM.show_status_of_case_studies(args['filter_regex'], args['short'],
                                        args['list_revs'])
    elif args['subcommand'] == 'gen':
        if args['git_path'].endswith(".git"):
            git_path = Path(args['git_path'][:-4])
        else:
            git_path = Path(args['git_path'])
        args['git_path'] = git_path

        cmap = generate_commit_map(git_path, args['end'],
                                   args['start'] if 'start' in args else None)

        args['paper_config_path'] = Path(args['paper_config_path'])
        if not args['paper_config_path'].exists():
            raise argparse.ArgumentTypeError("Paper path does not exist")

        case_study = generate_case_study(
            args['distribution'], args['num_rev'], cmap,
            git_path.stem.replace("-HEAD", ""), args['version'], **args)
        store_case_study(case_study, args['paper_config_path'])
    elif args['subcommand'] == 'ext':
        pass


def main_develop():
    """
    Handle and simplify common developer interactions with the project.
    """
    parser = argparse.ArgumentParser("Developer helper")
    sub_parsers = parser.add_subparsers(help="Sub commands", dest="command")

    # new-branch
    new_branch_parser = sub_parsers.add_parser('new-branch')
    new_branch_parser.add_argument(
        'branch_name', type=str, help='Name of the new branch')
    new_branch_parser.add_argument(
        'projects',
        nargs='+',
        action=enum_action(LLVMProjects),
        help="Projects to work on.")

    # checkout
    checkout_parser = sub_parsers.add_parser('checkout')
    checkout_parser.add_argument(
        'branch_name', type=str, help='Name of the new branch')
    checkout_parser.add_argument(
        'projects',
        nargs='+',
        action=enum_action(LLVMProjects),
        help="Projects to work on.")
    checkout_parser.add_argument('-r', '--remote', action='store_true')

    # git pull
    pull_parser = sub_parsers.add_parser('pull')
    pull_parser.add_argument(
        'projects',
        nargs='+',
        action=enum_action(LLVMProjects),
        help="Projects to work on.")

    # git push
    push_parser = sub_parsers.add_parser('push')
    push_parser.add_argument(
        'projects',
        nargs='+',
        action=enum_action(LLVMProjects),
        help="Projects to work on.")

    # git status
    status_parser = sub_parsers.add_parser('status')
    status_parser.add_argument(
        'projects',
        nargs='+',
        action=enum_action(LLVMProjects),
        help="Projects to work on.")

    # list dev-branches
    status_parser = sub_parsers.add_parser(
        'f-branches', help="List all remote feature branches")

    args = parser.parse_args()
    if args.command == 'new-branch':
        dev.create_new_branch_for_projects(args.branch_name, args.projects)
    elif args.command == 'checkout':
        if args.remote:
            dev.checkout_remote_branch_for_projects(args.branch_name,
                                                    args.projects)
        else:
            dev.checkout_branch_for_projects(args.branch_name, args.projects)
    elif args.command == 'pull':
        dev.pull_projects(args.projects)
    elif args.command == 'push':
        dev.push_projects(args.projects)
    elif args.command == 'status':
        dev.show_status_for_projects(args.projects)
    elif args.command == 'f-branches':
        dev.show_dev_branches(
            [LLVMProjects.llvm, LLVMProjects.clang, LLVMProjects.vara])
    else:
        parser.print_help()
