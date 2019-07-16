"""
Settings module for VaRA

All settings are stored in a simple dictionary. Each
setting should be modifiable via environment variable.
"""

import typing as tp
from os import path, makedirs, getcwd

import benchbuild.utils.settings as s

CFG = s.Configuration(
    "vara",
    node={
        "config_file": {
            "desc": "Config file path of varats. Not guaranteed to exist.",
            "default": None,
        },
        "version": {
            "desc": "VaRA version.",
            "default": 80,
        },
        "benchbuild_root": {
            "desc": "Root folder to run BenchBuild in",
            "default": None,
        },
        "llvm_source_dir": {
            "desc": "LLVM source dir",
            "default": None,
        },
        "llvm_install_dir": {
            "desc": "Install dir for LLVM and VaRA",
            "default": None,
        },
        "result_dir": {
            "desc": "Result folder for collected results",
            "default": None,
        },
        "own_libgit2": {
            "default": True,
            "desc": "Build own libgit2",
        },
        "include_phasar": {
            "default": True,
            "desc": "Include Phasar for static analysis",
        },
    })

CFG["paper_config"] = {
    "folder": {
        "desc": "Folder with paper configs.",
        "default": None,
    },
    "current_config": {
        "desc": "Paper config file to load.",
        "default": None,
    },
}

CFG["env"] = {
    "default": {},
    "desc": "The environment benchbuild's commands should operate in."
}

CFG['db'] = {
    "connect_string": {
        "desc":
        "sqlalchemy connect string",
        "default":
        "sqlite://"
    },
    "rollback": {
        "desc": "Rollback all operations after benchbuild completes.",
        "default": False
    },
    "create_functions": {
        "default": False,
        "desc": "Should we recreate our SQL functions from scratch?"
    }
}

CFG['experiment'] = {
    "only_missing": {
        "default": False,
        "desc": "Only run missing version"
    },
    "random_order": {
        "default": False,
        "desc": "Randomize the order of versions to explore."
    },
    "sample_limit": {
        "default": None,
        "desc": "Randomize the order of versions to explore."
    },
}

CFG['plots'] = {
    "data_cache": {
        "default": "data_cache",
        "desc": "Local data cache to store preprocessed files."
    },
}


def get_value_or_default(cfg: s.Configuration, varname: str,
                         default: tp.Any) -> tp.Any:
    """
    Checks if the config variable has a value and if it is not None.
    Then the value is returned. Otherwise, the default value is
    set and then returned.
    """
    config_node = cfg[varname]
    if not config_node.has_value or config_node.value is None:
        cfg[varname] = default
    return config_node.value


def create_missing_folders() -> None:
    """
    Create a folders that do not exist but where set in the config.
    """

    def create_missing_folder_for_cfg(
            cfg_varname: str, local_cfg: s.Configuration = CFG) -> None:
        """
        Create missing folders for a specific config path.
        """

        config_node = local_cfg[cfg_varname]
        if config_node.has_value and\
                config_node.value is not None and\
                not path.isdir(config_node.value):
            makedirs(config_node.value)

    create_missing_folder_for_cfg("benchbuild_root")
    create_missing_folder_for_cfg("result_dir")
    create_missing_folder_for_cfg("data_cache", CFG["plots"])


def save_config() -> None:
    """
    Persist VaRA config to a yaml file.
    """
    if CFG["config_file"].value is None:
        config_file = ".vara.yaml"
    else:
        config_file = str(CFG["config_file"])
    CFG["config_file"] = path.abspath(config_file)
    if CFG["result_dir"].value is None:
        CFG["result_dir"] = path.dirname(str(CFG["config_file"])) +\
            "/results"

    create_missing_folders()
    CFG.store(config_file)


def generate_benchbuild_config(vara_cfg: s.Configuration,
                               bb_config_path: str) -> None:
    """
    Generate a configuration file for benchbuild
    """
    from benchbuild.settings import CFG as BB_CFG

    # Projects for VaRA
    projects_conf = BB_CFG["plugins"]["projects"]
    # If we want later to use default BB projects
    # projects_conf.value[:] = [ x for x in projects_conf.value
    #                           if not x.endswith('gzip')]
    projects_conf.value[:] = []
    projects_conf.value[:] += [
        'varats.projects.c_projects.busybox',
        'varats.projects.c_projects.git',
        'varats.projects.c_projects.gravity',
        'varats.projects.c_projects.gzip',
        'varats.projects.c_projects.libvpx',
        'varats.projects.c_projects.lrzip',
        'varats.projects.c_projects.opus',
        'varats.projects.c_projects.tmux',
        'varats.projects.c_projects.vim',
        'varats.projects.c_projects.x264',
        'varats.projects.c_projects.xz',
    ]
    projects_conf.value[:] += ['varats.projects.cpp_projects.doxygen']
    projects_conf.value[:] += ['varats.projects.test_projects.basic_tests']

    # Experiments for VaRA
    projects_conf = BB_CFG["plugins"]["experiments"]
    projects_conf.value[:] = []
    projects_conf.value[:] += [
        'varats.experiments.git_blame_annotation_report',
        'varats.experiments.marker_tester',
        'varats.experiments.just_compile'
    ]

    BB_CFG["env"] = {"PATH": [str(vara_cfg["llvm_install_dir"]) + "bin/"]}

    # Add VaRA experiment config variables
    BB_CFG["vara"] = {
        "outfile": {
            "default": "",
            "desc": "Path to store results of VaRA CFR analysis.",
            "value": str(vara_cfg["result_dir"])
        },
        "result": {
            "default": "",
            "desc": "Path to store already annotated projects.",
            "value": "BC_files"
        }
    }

    def replace_bb_cwd_path(cfg_varname: str,
                            cfg_node: s.Configuration = BB_CFG) -> None:
        cfg_node[cfg_varname] = str(vara_cfg["benchbuild_root"]) +\
            str(cfg_node[cfg_varname])[len(getcwd()):]

    replace_bb_cwd_path("build_dir")
    replace_bb_cwd_path("tmp_dir")
    replace_bb_cwd_path("test_dir")
    replace_bb_cwd_path("node_dir", BB_CFG["slurm"])

    # Create caching folder for .bc files
    BC_cache_path = str(vara_cfg["benchbuild_root"])
    BC_cache_path += "/" + str(BB_CFG["vara"]["result"])
    if not path.isdir(BC_cache_path):
        makedirs(BC_cache_path)

    BB_CFG.store(bb_config_path)


s.setup_config(CFG, ['.vara.yaml', '.vara.yml'], "VARA_CONFIG_FILE")
s.update_env(CFG)
