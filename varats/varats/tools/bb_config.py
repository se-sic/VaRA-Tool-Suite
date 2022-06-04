"""
This module handles the configuration of Benchbuild.

It can automatically create different preconfigured configs for BB.
"""
import os.path
from copy import deepcopy

from benchbuild.utils import settings as s

from varats.tools.tool_util import (
    get_supported_research_tool_names,
    get_research_tool_type,
)
from varats.utils.settings import add_vara_experiment_options


def create_new_bb_config(
    varats_cfg: s.Configuration,
    include_test_projects: bool = False
) -> s.Configuration:
    """
    Create a new default bb config.

    For internal use only! If you want to access the current bb config, use
    :func:`bb_cfg()` instead.

    Args:
        varats_cfg: the varats config this bb config is based on
        include_test_projects: changes whether test projects are included

    Returns:
        a new default bb config object
    """
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
        'varats.projects.c_projects.brotli',
        'varats.projects.c_projects.bzip2',
        'varats.projects.c_projects.coreutils',
        'varats.projects.c_projects.curl',
        'varats.projects.c_projects.file',
        'varats.projects.c_projects.gawk',
        'varats.projects.c_projects.git',
        'varats.projects.c_projects.glib',
        'varats.projects.c_projects.glibc',
        'varats.projects.c_projects.gravity',
        'varats.projects.c_projects.grep',
        'varats.projects.c_projects.gzip',
        'varats.projects.c_projects.htop',
        'varats.projects.c_projects.irssi',
        'varats.projects.c_projects.libjpeg_turbo',
        'varats.projects.c_projects.libpng',
        'varats.projects.c_projects.libsigrok',
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
        'varats.projects.cpp_projects.libzmq',
        'varats.projects.cpp_projects.mongodb',
        'varats.projects.cpp_projects.poppler',
    ]
    projects_conf.value[:] += [
        'varats.projects.cpp_projects.doxygen', 'varats.projects.cpp_projects'
        '.two_libs_one_project_interaction_discrete_libs_single_project'
    ]
    if include_test_projects:
        projects_conf.value[:] += [
            'varats.projects.test_projects.basic_tests',
            'varats.projects.test_projects.bug_provider_test_repos',
            'varats.projects.test_projects.example_test_repo',
            'varats.projects.test_projects.linker_check',
            'varats.projects.test_projects.taint_tests',
            'varats.projects.test_projects.test_suite',
            'varats.projects.perf_tests.feature_perf_cs_collection'
        ]

    # Experiments for VaRA
    projects_conf = new_bb_cfg["plugins"]["experiments"]
    projects_conf.value[:] = []
    projects_conf.value[:] += [
        'varats.experiments.base.just_compile',
        'varats.experiments.vara.blame_report_experiment',
        'varats.experiments.vara.commit_report_experiment',
        'varats.experiments.vara.feature_perf_runner',
        'varats.experiments.vara.feature_perf_analysis_experiments',
        'varats.experiments.vara.instrumentation_point_printer',
        'varats.experiments.vara.instrumentation_stats',
        'varats.experiments.vara.marker_tester',
        'varats.experiments.vara.blame_verifier_experiment',
        'varats.experiments.vara.phasar_fta',
        'varats.experiments.phasar.ide_linear_constant_experiment',
        'varats.experiments.phasar.global_analysis_compare',
        'varats.experiments.szz.szz_unleashed_experiment',
        'varats.experiments.szz.pydriller_szz_experiment',
    ]

    # Enable version exploration by default
    new_bb_cfg["versions"]["full"] = True

    # Slurm Cluster Configuration
    new_bb_cfg["slurm"]["account"] = "anywhere"
    new_bb_cfg["slurm"]["partition"] = "anywhere"

    # Container pre Configuration
    new_bb_cfg["container"]["mounts"] = [
        [varats_cfg["result_dir"].value, "/varats_root/results"],
        [f"{varats_cfg['benchbuild_root']}/BC_files", "/varats_root/BC_files"],
        [
            varats_cfg["paper_config"]["folder"].value,
            "/varats_root/paper_configs"
        ],
    ]

    new_bb_cfg["env"] = {
        "PATH": [
            str(tool_type.install_location() / "bin") for tool_type in [
                get_research_tool_type(tool_name)
                for tool_name in get_supported_research_tool_names()
            ] if tool_type.has_install_location()
        ]
    }

    # Add VaRA experiment config variables
    add_vara_experiment_options(new_bb_cfg, varats_cfg)

    # Set paths to defaults
    bb_root = str(varats_cfg["benchbuild_root"])
    new_bb_cfg["build_dir"] = s.ConfigPath(os.path.join(bb_root, "results"))
    new_bb_cfg["tmp_dir"] = s.ConfigPath(os.path.join(bb_root, "tmp"))
    new_bb_cfg["slurm"]["node_dir"] = s.ConfigPath(
        os.path.join(bb_root, "results")
    )
    new_bb_cfg["slurm"]["logs"] = s.ConfigPath(
        os.path.join(bb_root, "slurm_logs")
    )
    new_bb_cfg["container"]["root"] = s.ConfigPath(
        os.path.join(bb_root, "containers", "lib")
    )
    new_bb_cfg["container"]["runroot"] = s.ConfigPath(
        os.path.join(bb_root, "containers", "run")
    )
    new_bb_cfg["container"]["export"] = s.ConfigPath(
        os.path.join(bb_root, "containers", "export")
    )
    new_bb_cfg["container"]["import"] = s.ConfigPath(
        os.path.join(bb_root, "containers", "export")
    )
    new_bb_cfg["container"]["source"] = None

    # will be set correctly when saved
    new_bb_cfg["config_file"] = None

    return new_bb_cfg
