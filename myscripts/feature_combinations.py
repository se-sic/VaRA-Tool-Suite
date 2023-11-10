#!/usr/bin/env python3
from sys import argv

from common import load_feature_model, getConfigs, config_to_options
from feature_option_mapping import feature_option_mapping


def wrap_ticks(wrappee):
    # Split spaces
    #splitted_wrappee = []
    #for x in wrappee:
    #    splitted_wrappee.extend(x.split(" ", 1))

    return map(lambda x: f'"{x}"', wrappee)


def create_mapping(configs, feature_to_options):
    mapping = {}

    id = 0
    for config in configs:
        to_add = f"""'[{', '.join(wrap_ticks(config_to_options(config, feature_to_options)))}]'"""
        if to_add not in mapping.values():
            mapping[id] = to_add
            id += 1

    # test mapping unique
    assert len(mapping.values()
              ) == len(set(mapping.values())), "Mapping contains duplicates!"

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
