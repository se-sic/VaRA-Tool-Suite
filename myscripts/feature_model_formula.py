#!/usr/bin/env python3
from sys import argv

from common import (
    load_feature_model,
    getConfigs,
    replace_feature_with_option,
    remove_empty,
)
from feature_option_mapping import feature_option_mapping


def options_to_formula(options):
    output = []
    for option, value in options.items():
        if value is 0 or value:
            output.append(option)
        else:
            output.append(f"~{option}")
    return f"({' & '.join(output)})"


def dnf_formula(configs, feature_to_options):
    output = []
    for config in configs:
        options = remove_empty(
            replace_feature_with_option(config, feature_to_options)
        )
        conjunction = options_to_formula(options)
        if conjunction not in output:
            output.append(conjunction)

    assert len(output) == len(set(output)), "Formula not unique"
    return " | ".join(output)


def main():
    fm = load_feature_model(argv[1])
    feature_to_options = feature_option_mapping(fm, lstrip="-")
    configs = getConfigs(fm)
    print(dnf_formula(configs, feature_to_options))


if __name__ == "__main__":
    main()
