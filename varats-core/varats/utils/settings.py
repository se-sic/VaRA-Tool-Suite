"""
Settings module for VaRA.

All settings are stored in a simple dictionary. Each setting should be
modifiable via environment variable.
"""
import os
import typing as tp
from os import makedirs, path
from pathlib import Path

import benchbuild.utils.settings as s
from plumbum import local, LocalPath


def create_new_varats_config() -> s.Configuration:
    """
    Create a new default (uninitialized) varats config.

    For internal use only! If you want to access the current varats config, use
    :func:`vara_cfg()` instead.

    Returns:
        a new default vara config object
    """
    cfg = s.Configuration(
        "varats",
        node={
            "config_file": {
                "desc": "Config file path of varats. Not guaranteed to exist.",
                "default": None,
            },
            "benchbuild_root": {
                "desc": "Root folder to run BenchBuild in",
                "default": os.getcwd() + "/benchbuild",
            },
            "data_cache": {
                "desc": "Local data cache to store preprocessed files.",
                "default": os.getcwd() + "/data_cache",
            },
            "result_dir": {
                "desc": "Result folder for collected results",
                "default": os.getcwd() + "/results",
            },
        }
    )

    cfg["container"] = {
        "research_tool": {
            "desc":
                "The currently active research tool."
                "Base containers come with this tool preinstalled.",
            "default": None
        },
        "from_source": {
            "desc":
                "Whether to install varats in the container from a local "
                "source checkout or pip.",
            "default": False
        },
        "dev_mode": {
            "desc":
                "If enabled, install varats in editable mode."
                "Implies `from_source=True` and `varats_source` must be "
                "mountable inside the container.",
            "default": False
        },
        "varats_source": {
            "desc":
                "Path to the local checkout of varats to use for the source"
                "install.",
            "default": None
        }
    }

    cfg["vara"] = {
        "version": {
            "desc": "VaRA version.",
            "default": 120,
        },
        "llvm_source_dir": {
            "desc": "LLVM source dir",
            "default": None,
        },
        "llvm_install_dir": {
            "desc": "Install dir for LLVM and VaRA",
            "default": None,
        },
        "own_libgit2": {
            "default": True,
            "desc": "Build own libgit2 [Deprecated]",
        },
        "with_phasar": {
            "default": True,
            "desc": "Include Phasar for static analysis [Deprecated]",
        },
        "developer_version": {
            "desc": "Setup VaRA as development build.",
            "default": True,
        },
    }

    cfg["phasar"] = {
        "source_dir": {
            "desc": "Phasar source directory",
            "default": None
        },
        "install_dir": {
            "desc": "Phasar install directory",
            "default": None
        },
        "developer_version": {
            "desc": "Setup phasar as development build.",
            "default": True,
        },
    }

    cfg["szzunleashed"] = {
        "source_dir": {
            "desc": "SZZUnleashed source directory",
            "default": None
        },
        "install_dir": {
            "desc": "SZZUnleashed install directory",
            "default": None
        },
    }

    cfg["paper_config"] = {
        "folder": {
            "desc": "Folder with paper configs.",
            "default": os.getcwd() + "/paper_configs",
        },
        "current_config": {
            "desc": "Paper config file to load.",
            "default": None,
        },
    }

    cfg["env"] = {
        "default": {},
        "desc": "The environment benchbuild's commands should operate in."
    }

    cfg['db'] = {
        "connect_string": {
            "desc": "sqlalchemy connect string",
            "default": "sqlite://"
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

    cfg['experiment'] = {
        "only_missing": {
            "default": True,
            "desc":
                "Only run missing version [Deprecated]"
                "This option is replaced by file_status_blacklist = [Success]"
        },
        "file_status_blacklist": {
            "default": ['Success', 'Blocked'],
            "desc":
                "Do not include revision with these file status for benchbuild "
                "processing"
        },
        "file_status_whitelist": {
            "default": [],
            "desc":
                "Only include revision with these file status for benchbuild "
                "processing"
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

    cfg['plots'] = {
        "plot_dir": {
            "desc": "Folder for generated plots",
            "default": os.getcwd() + "/plots",
        },
    }

    cfg['tables'] = {
        "table_dir": {
            "desc": "Folder for generated tables",
            "default": os.getcwd() + "/tables",
        },
    }

    cfg['artefacts'] = {
        "artefacts_dir": {
            "desc": "Folder for generated artefacts",
            "default": os.getcwd() + "/artefacts",
        },
    }

    cfg['provider'] = {
        "github_access_token": {
            "desc": "GitHub access token",
            "default": None,
        }
    }

    cfg['sampling'] = {}

    cfg['ml'] = {}
    return cfg


_CFG: tp.Optional[s.Configuration] = None
_BB_CFG: tp.Optional[s.Configuration] = None


def vara_cfg() -> s.Configuration:
    """Get the current vara config."""
    global _CFG  # pylint: disable=global-statement
    if not _CFG:
        _CFG = create_new_varats_config()
        s.setup_config(
            _CFG, ['.varats.yaml', '.varats.yml'], "VARATS_CONFIG_FILE"
        )
        s.update_env(_CFG)
    return _CFG


def add_vara_experiment_options(
    benchbuild_config: s.Configuration, varats_config: s.Configuration
) -> None:
    """Add varats specific options to a benchbuild config."""
    benchbuild_config["varats"] = {
        "outfile": {
            "default": "",
            "desc": "Path to store results of VaRA CFR analysis.",
            "value": s.ConfigPath(str(varats_config["result_dir"]))
        },
        "result": {
            "default":
                "missingPath/annotatedResults",
            "desc":
                "Path to store already annotated projects.",
            "value":
                s.ConfigPath(
                    os.path.join(
                        str(vara_cfg()["benchbuild_root"]), "BC_files"
                    )
                )
        }
    }


def bb_cfg() -> s.Configuration:
    """Get the current benchbuild config."""
    global _BB_CFG  # pylint: disable=global-statement
    if not _BB_CFG:
        from benchbuild.settings import CFG as BB_CFG  # pylint: disable=C0415
        add_vara_experiment_options(BB_CFG, vara_cfg())
        bb_root = str(vara_cfg()["benchbuild_root"])
        if bb_root:
            bb_cfg_path = Path(bb_root) / ".benchbuild.yml"
            if bb_cfg_path.exists():
                BB_CFG.load(local.path(bb_cfg_path))
        _BB_CFG = BB_CFG
    return _BB_CFG


def get_value_or_default(
    cfg: s.Configuration, varname: str, default: tp.Any
) -> tp.Any:
    """
    Checks if the config variable has a value and if it is not None.

    Then the value is returned. Otherwise, the default value is set and then
    returned.
    """
    config_node = cfg[varname]
    if not config_node.has_value or config_node.value is None:
        cfg[varname] = default
    return config_node.value


def create_missing_folders() -> None:
    """Create folders that do not exist but were set in the config."""

    def create_missing_folder_for_cfg(
        cfg_varname: str, local_cfg: s.Configuration = vara_cfg()
    ) -> None:
        """Create missing folders for a specific config path."""

        config_node = local_cfg[cfg_varname]
        if config_node.has_value() and\
                config_node.value is not None and\
                not path.isdir(config_node.value):
            makedirs(config_node.value)

    create_missing_folder_for_cfg("benchbuild_root")
    create_missing_folder_for_cfg("result_dir")
    create_missing_folder_for_cfg("data_cache")
    create_missing_folder_for_cfg("folder", vara_cfg()["paper_config"])
    create_missing_folder_for_cfg("plot_dir", vara_cfg()["plots"])
    create_missing_folder_for_cfg("table_dir", vara_cfg()["tables"])
    create_missing_folder_for_cfg("artefacts_dir", vara_cfg()["artefacts"])


def save_config() -> None:
    """Persist VaRA config to a yaml file."""
    if vara_cfg()["config_file"].value is None:
        config_file = ".varats.yaml"
    else:
        config_file = str(vara_cfg()["config_file"])

    vara_cfg()["config_file"] = path.abspath(config_file)
    create_missing_folders()
    vara_cfg().store(LocalPath(config_file))


def save_bb_config(benchbuild_cfg: tp.Optional[s.Configuration] = None) -> None:
    """Persist BenchBuild config to a yaml file."""
    if not benchbuild_cfg:
        benchbuild_cfg = bb_cfg()

    config_file = local.path(
        str(vara_cfg()["benchbuild_root"])
    ) / ".benchbuild.yml"
    benchbuild_cfg["config_file"] = str(config_file)
    benchbuild_cfg.store(config_file)


def get_varats_base_folder() -> Path:
    """
    Returns the path to the tool suite base folder, i.e., the folder that
    contains the config file.

    Returns:
        path to base folder
    """
    cfg_config_file = vara_cfg()["config_file"].value
    if cfg_config_file is None:
        raise ValueError("No config file found.")
    return Path(cfg_config_file).parent
