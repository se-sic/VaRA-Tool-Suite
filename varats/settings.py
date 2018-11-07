"""
Settings module for VaRA

All settings are stored in a simple dictionary. Each
setting should be modifiable via environment variable.
"""

from os import path, makedirs

import benchbuild.utils.settings as s

CFG = s.Configuration(
    "vara",
    node = {
        "config_file": {
            "desc": "Config file path of varats. Not guaranteed to exist.",
            "default": None,
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
    }
)

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


def get_value_or_default(CFG, varname, default):
    """
    Checks if the config variable has a value and if it is not None.
    Then the value is returned. Otherwise, the default value is
    set and then returned.
    """
    config_node = CFG[varname]
    if not config_node.has_value or config_node.value is None:
        CFG[varname] = default
    return config_node.value


def create_missing_folders():
    """
    Create a folders that do not exist but where set in the config.
    """
    def create_missing_folder_for_cfg(cfg_varname):
        config_node = CFG[cfg_varname]
        if config_node.has_value and\
                config_node.value is not None and\
                not path.isdir(config_node.value):
            makedirs(config_node.value)

    create_missing_folder_for_cfg("benchbuild_root")
    create_missing_folder_for_cfg("result_dir")


def save_config():
    """
    Persist VaRA config to a yaml file.
    """
    if CFG["config_file"].value == None:
        config_file = ".vara.yaml"
    else:
        config_file = str(CFG["config_file"])
    CFG["config_file"] = path.abspath(config_file)
    if CFG["result_dir"].value is None:
        CFG["result_dir"] = path.dirname(str(CFG["config_file"])) +\
            "/results"

    create_missing_folders()
    CFG.store(config_file)


s.setup_config(CFG,['.vara.yaml', '.vara.yml'])
s.update_env(CFG)
