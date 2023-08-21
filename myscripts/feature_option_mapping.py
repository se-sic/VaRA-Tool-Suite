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


def feature_option_mapping(fm):
    output = {}
    for feature in fm:
        name = feature.name.str()
        option = feature.output_string.str()
        numeric_values = get_numeric_values(feature)
        if numeric_values:
            output[name] = [f"{option}{i}" for i in numeric_values]
        else:
            output[name] = option
    return output


def main():
    fm = load_feature_model(argv[1])
    print(json.dumps(feature_option_mapping(fm)))


if __name__ == "__main__":
    main()
