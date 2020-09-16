"""
Settings module for VaRA.

All settings are stored in a simple dictionary. Each setting should be
modifiable via environment variable.
"""

import typing as tp
from os import makedirs, path
from pathlib import Path

import benchbuild.utils.settings as s

_CFG = s.Configuration(
    "varats",
    node={
        "config_file": {
            "desc": "Config file path of varats. Not guaranteed to exist.",
            "default": None,
        },
        "benchbuild_root": {
            "desc": "Root folder to run BenchBuild in",
            "default": None,
        },
        "data_cache": {
            "default": "data_cache",
            "desc": "Local data cache to store preprocessed files."
        },
        "result_dir": {
            "desc": "Result folder for collected results",
            "default": None,
        },
    }
)

_CFG["vara"] = {
    "version": {
        "desc": "VaRA version.",
        "default": 100,
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

_CFG["phasar"] = {
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

_CFG["paper_config"] = {
    "folder": {
        "desc": "Folder with paper configs.",
        "default": None,
    },
    "current_config": {
        "desc": "Paper config file to load.",
        "default": None,
    },
}

_CFG["env"] = {
    "default": {},
    "desc": "The environment benchbuild's commands should operate in."
}

_CFG['db'] = {
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

_CFG['experiment'] = {
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

_CFG['plots'] = {
    "plot_dir": {
        "desc": "Folder for generated plots",
        "default": None,
    },
}

_CFG['tables'] = {
    "table_dir": {
        "desc": "Folder for generated tables",
        "default": None,
    },
}

_CFG['artefacts'] = {
    "artefacts_dir": {
        "desc": "Folder for generated artefacts",
        "default": None,
    },
}

_CFG['provider'] = {
    "github_access_token": {
        "desc": "GitHub access token",
        "default": None,
    }
}


def vara_cfg() -> s.Configuration:
    """Get the current vara config."""
    return _CFG


_BB_CFG: tp.Optional[s.Configuration] = None


def bb_cfg() -> s.Configuration:
    """Get the current behcnbuild config."""
    global _BB_CFG  # pylint: disable=global-statement
    if not _BB_CFG:
        from benchbuild.settings import CFG as BB_CFG  # pylint: disable=C0415
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
        cfg_varname: str, local_cfg: s.Configuration = _CFG
    ) -> None:
        """Create missing folders for a specific config path."""

        config_node = local_cfg[cfg_varname]
        if config_node.has_value and\
                config_node.value is not None and\
                not path.isdir(config_node.value):
            makedirs(config_node.value)

    create_missing_folder_for_cfg("benchbuild_root")
    create_missing_folder_for_cfg("result_dir")
    create_missing_folder_for_cfg("data_cache", _CFG)
    create_missing_folder_for_cfg("plot_dir", _CFG["plots"])
    create_missing_folder_for_cfg("table_dir", _CFG["tables"])
    create_missing_folder_for_cfg("artefacts_dir", _CFG["artefacts"])


def save_config() -> None:
    """Persist VaRA config to a yaml file."""
    if _CFG["config_file"].value is None:
        config_file = ".varats.yaml"
    else:
        config_file = str(_CFG["config_file"])
    _CFG["config_file"] = path.abspath(config_file)
    if _CFG["result_dir"].value is None:
        _CFG["result_dir"] = path.dirname(str(_CFG["config_file"])) + "/results"
    if _CFG["plots"]["plot_dir"].value is None:
        _CFG["plots"]["plot_dir"] = path.dirname(
            str(_CFG["config_file"])
        ) + "/plots"
    if _CFG["tables"]["table_dir"].value is None:
        _CFG["tables"]["table_dir"] = path.dirname(
            str(_CFG["config_file"])
        ) + "/tables"

    create_missing_folders()
    _CFG.store(config_file)


def get_varats_base_folder() -> Path:
    """
    Returns the path to the tool suite base folder, i.e., the folder that
    contains the config file.

    Returns:
        path to base folder
    """
    cfg_config_file = _CFG["config_file"].value
    if cfg_config_file is None:
        raise ValueError("No config file found.")
    return Path(cfg_config_file).parent


s.setup_config(_CFG, ['.varats.yaml', '.varats.yml'], "VARATS_CONFIG_FILE")
s.update_env(_CFG)
