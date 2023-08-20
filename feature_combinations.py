#!/usr/bin/env python3
from sys import argv

import vara_feature.feature_model as FM
from more_itertools import powerset
from vara_feature.configuration import (
    Configuration,
    ConfigurationOption,
    getAllConfigs,
)


def load_feature_model(path):
    fm = FM.loadFeatureModel(path)
    if fm is None:
        raise ValueError("Feature Model could not be loaded!")
    return fm


def getConfigs(fm):
    configs = []
    for config in getAllConfigs(fm):
        options = dict()
        for option in config.getOptions():
            name = option.name
            value: str = option.value
            if value == "true":
                options[name] = True
            elif value == "false":
                options[name] = False
            elif value.isdigit():
                option[name] = int(value)
            else:
                option[name] = value
        configs.append(options)
    return configs


def config_to_options(config):
    options = []
    for key, value in config.items():
        if isinstance(value, bool):
            if value:
                options.append(key)
        else:
            raise NotImplementedError()
    return options


def wrap_ticks(wrappee):
    return map(lambda x: f'"{x}"', wrappee)


def create_mapping(configs):
    mapping = {}

    for id, config in enumerate(configs):
        mapping[id
               ] = f"""'[{', '.join(wrap_ticks(config_to_options(config)))}]'"""

    return mapping


def formatted_print(mapping):
    for id in mapping:
        print(f"    - {id}")

    tmp = []
    for id, config in mapping.items():
        tmp.append(f"{id}: {config}")

    print(f"""version: 0
...
---
{chr(10).join(tmp)}
...
""")


def main():
    fm = load_feature_model(argv[1])
    configs = getConfigs(fm)
    mapping = create_mapping(configs)
    formatted_print(mapping)


if __name__ == "__main__":
    main()
