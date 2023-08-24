#!/usr/bin/env python3
import json
import re
import typing as tp
from sys import argv

from common import load_feature_model
from vara_feature.feature import NumericFeature, Feature

REGEX_MIN_VALUE = re.compile("minValue: (\d+)")
REGEX_MAX_VALUE = re.compile("maxValue: (\d+)")
REGEX_VALUES = re.compile("values: [(.+)]")


def get_min_value(s: str) -> tp.Optional[int]:
    if (result := REGEX_MIN_VALUE.search(s)):
        return int(result.group(1))
    return None


def get_max_value(s: str) -> tp.Optional[int]:
    if (result := REGEX_MAX_VALUE.search(s)):
        return int(result.group(1))
    return None


def get_values(s: str) -> tp.Optional[tp.List[int]]:
    if (result := REGEX_VALUES.search(s)):
        values = result.group(1).split(",")
        return list(map(int, values))
    return None


def get_numeric_values(feature: Feature) -> tp.Optional[tp.List[int]]:
    s = feature.to_string()
    if isinstance(feature, NumericFeature):
        _get_values = get_values(s)
        if _get_values:
            return _get_values
        return range(get_min_value(s), get_max_value(s) + 1)[:10]

    return None


def strip_prefix(dictionary, prefix_chars):
    out = {}
    for key, value in dictionary.items():
        if isinstance(value, tuple):
            out[key] = tuple(x.lstrip(prefix_chars) for x in value)
        else:
            out[key] = value.lstrip(prefix_chars)
    return out


def prefix_numeric(dictionary, prefix):
    out = {}
    for key, value in dictionary.items():
        if isinstance(value, tuple):
            out[key] = tuple(f"{prefix}{x}" for x in value if x.isnumeric())
        else:
            if value.isnumeric():
                out[key] = f"{prefix}{value}"
            else:
                out[key] = value
    return out


def feature_option_mapping(fm, lstrip=None, numeric_prefix=None):
    output = {}
    for feature in fm:
        name = feature.name.str()
        option = feature.output_string.str()
        numeric_values = get_numeric_values(feature)
        if numeric_values:
            output[name] = tuple(f"{option}{i}" for i in numeric_values)
        else:
            output[name] = option
    if lstrip is not None:
        output = strip_prefix(output, lstrip)
    if numeric_prefix is not None:
        output = prefix_numeric(output, numeric_prefix)
    return output


def main():
    fm = load_feature_model(argv[1])
    print(json.dumps(feature_option_mapping(fm)))


if __name__ == "__main__":
    main()
