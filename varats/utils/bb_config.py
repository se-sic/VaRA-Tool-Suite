"""
This module handles the configuration of Benchbuild.

It can automatically create different preconfigured configs for BB.
"""

from copy import deepcopy
from os import getcwd, makedirs, path

import benchbuild.utils.settings as s

from varats.utils.cli_util import (
    get_supported_research_tool_names,
    get_research_tool_type,
)


def generate_benchbuild_config(
    varats_cfg: s.Configuration, bb_config_path: str
) -> None:
    """Generate a configuration file for benchbuild."""
    from benchbuild.settings import CFG as BB_CFG  # pylint: disable=C0415
    new_bb_cfg = deepcopy(BB_CFG)

    # Projects for VaRA
    projects_conf = new_bb_cfg["plugins"]["projects"]
    # If we want later to use default BB projects
    # projects_conf.value[:] = [ x for x in projects_conf.value
    #                           if not x.endswith('gzip')]
    projects_conf.value[:] = []
    projects_conf.value[:] += [
        'varats.projects.c_projects.bison',
        'varats.projects.c_projects.bitlbee',
        'varats.projects.c_projects.busybox',
        'varats.projects.c_projects.coreutils',
        'varats.projects.c_projects.curl',
        'varats.projects.c_projects.gawk',
        'varats.projects.c_projects.git',
        'varats.projects.c_projects.gravity',
        'varats.projects.c_projects.gzip',
        'varats.projects.c_projects.htop',
        'varats.projects.c_projects.irssi',
        'varats.projects.c_projects.libpng',
        'varats.projects.c_projects.libssh',
        'varats.projects.c_projects.libtiff',
        'varats.projects.c_projects.libvpx',
        'varats.projects.c_projects.libxml2',
        'varats.projects.c_projects.lrzip',
        'varats.projects.c_projects.lz4',
        'varats.projects.c_projects.openssl',
        'varats.projects.c_projects.openvpn',
        'varats.projects.c_projects.opus',
        'varats.projects.c_projects.qemu',
        'varats.projects.c_projects.redis',
        'varats.projects.c_projects.tmux',
        'varats.projects.c_projects.vim',
        'varats.projects.c_projects.x264',
        'varats.projects.c_projects.xz',
        'varats.projects.cpp_projects.mongodb',
        'varats.projects.cpp_projects.poppler',
    ]
    projects_conf.value[:] += ['varats.projects.cpp_projects.doxygen']
    projects_conf.value[:] += ['varats.projects.test_projects.basic_tests']
    projects_conf.value[:] += ['varats.projects.test_projects.linker_check']
    projects_conf.value[:] += ['varats.projects.test_projects.taint_tests']

    # Experiments for VaRA
    projects_conf = new_bb_cfg["plugins"]["experiments"]
    projects_conf.value[:] = []
    projects_conf.value[:] += [
        'varats.experiments.base.just_compile',
        'varats.experiments.vara.phasar_env_analysis',
        'varats.experiments.vara.blame_report_experiment',
        'varats.experiments.vara.commit_report_experiment',
        'varats.experiments.vara.marker_tester',
        'varats.experiments.vara.vara_fc_taint_analysis',
        'varats.experiments.vara.vara_full_mtfa',
        'varats.experiments.vara.blame_verifier_experiment',
        'varats.experiments.phasar.ide_linear_constant_experiment',
    ]

    # Slurm Cluster Configuration
    new_bb_cfg["slurm"]["account"] = "anywhere"
    new_bb_cfg["slurm"]["partition"] = "anywhere"

    new_bb_cfg["env"] = {
        "PATH": [
            str(tool_type.install_location() / "bin") for tool_type in [
                get_research_tool_type(tool_name)
                for tool_name in get_supported_research_tool_names()
            ] if tool_type.has_install_location()
        ]
    }

    # Add VaRA experiment config variables
    new_bb_cfg["varats"] = {
        "outfile": {
            "default": "",
            "desc": "Path to store results of VaRA CFR analysis.",
            "value": str(varats_cfg["result_dir"])
        },
        "result": {
            "default": "",
            "desc": "Path to store already annotated projects.",
            "value": "BC_files"
        }
    }

    def replace_bb_cwd_path(
        cfg_varname: str, cfg_node: s.Configuration = new_bb_cfg
    ) -> None:
        cfg_node[cfg_varname] = str(varats_cfg["benchbuild_root"]) +\
            str(cfg_node[cfg_varname])[len(getcwd()):]

    replace_bb_cwd_path("build_dir")
    replace_bb_cwd_path("tmp_dir")
    # replace_bb_cwd_path("test_dir")
    replace_bb_cwd_path("node_dir", new_bb_cfg["slurm"])

    # Create caching folder for .bc files
    bc_cache_path = str(varats_cfg["benchbuild_root"])
    bc_cache_path += "/" + str(new_bb_cfg["varats"]["result"])
    if not path.isdir(bc_cache_path):
        makedirs(bc_cache_path)

    new_bb_cfg.store(bb_config_path)
