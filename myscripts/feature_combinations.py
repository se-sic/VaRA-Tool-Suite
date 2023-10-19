#!/usr/bin/env python3
from sys import argv

from common import load_feature_model, getConfigs, config_to_options
from feature_option_mapping import feature_option_mapping


def wrap_ticks(wrappee):
    return map(lambda x: f'"{x}"', wrappee)


def create_mapping(configs, feature_to_options):
    mapping = {}

    for id, config in enumerate(configs):
        mapping[
            id
        ] = f"""'[{', '.join(wrap_ticks(config_to_options(config, feature_to_options)))}]'"""

    return mapping


def formatted_print(mapping):
    for id in mapping:
        print(f"    - {id}")

    tmp = []
    for id, config in mapping.items():
        tmp.append(f"{id}: {config}")

    print(
        f"""version: 0
...
---
config_type: PlainCommandlineConfiguration
{chr(10).join(tmp)}
...
"""
    )


def main():
    fm = load_feature_model(argv[1])
    feature_to_options = feature_option_mapping(fm)
    configs = getConfigs(fm)
    mapping = create_mapping(configs, feature_to_options)
    formatted_print(mapping)


if __name__ == "__main__":
    main()
