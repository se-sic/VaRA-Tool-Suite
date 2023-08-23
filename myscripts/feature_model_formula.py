#!/usr/bin/env python3
from sys import argv

from common import load_feature_model, getConfigs
from feature_option_mapping import feature_option_mapping


def replace_feature_with_option(config, feature_to_options):
    out = {}
    for key, value in config.items():
        option = feature_to_options[key]
        if option:
            out[option] = value
    return out


def options_to_formula(options):
    output = []
    for option, value in options.items():
        if value:
            output.append(option)
        else:
            output.append(f"~{option}")
    return f"({' & '.join(output)})"


def dnf_formula(configs, feature_to_options):
    output = []
    for config in configs:
        options = replace_feature_with_option(config, feature_to_options)
        conjunction = options_to_formula(options)
        output.append(conjunction)
    return " | ".join(output)


def strip_dash(dictionary):
    out = {}
    for key, value in dictionary.items():
        if isinstance(value, list):
            for x in value:
                out[key] = x.lstrip("-")
        else:
            out[key] = value.lstrip("-")
    return out


def main():
    fm = load_feature_model(argv[1])
    feature_to_options = strip_dash(feature_option_mapping(fm))
    configs = getConfigs(fm)
    print(dnf_formula(configs, feature_to_options))


if __name__ == "__main__":
    main()
