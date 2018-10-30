"""
Settings module for VaRA

All settings are stored in a simple dictionary. Each
setting should be modifiable via environment variable.
"""

import benchbuild.utils.settings as s

CFG = s.Configuration(
    "vara",
    node = {
        "config_file": {
            "desc": "Config file path of varats. Not guaranteed to exist.",
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

s.setup_config(CFG,['.vara.yaml', '.vara.yml'])
s.update_env(CFG)
