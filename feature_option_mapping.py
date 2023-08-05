#!/usr/bin/env python3
import json
import re
from sys import argv

import vara_feature
import vara_feature.feature_model as FM
from vara_feature.feature import NumericFeature, Feature

REGEX_MIN_VALUE = re.compile("minValue: (\d+)")
REGEX_MAX_VALUE = re.compile("maxValue: (\d+)")
REGEX_VALUES = re.compile("values: [(.+)]")

fm = FM.loadFeatureModel(argv[1])


def get_min_value(s: str) -> int | None:
    if (result := REGEX_MIN_VALUE.search(s)):
        return int(result.group(1))
    return None


def get_max_value(s: str) -> int | None:
    if (result := REGEX_MAX_VALUE.search(s)):
        return int(result.group(1))
    return None


def get_values(s: str) -> list[int] | None:
    if (result := REGEX_VALUES.search(s)):
        values = result.group(1).split(",")
        return list(map(int, values))
    return None


def get_numeric_values(feature: Feature) -> list[int] | None:
    s = feature.to_string()
    if isinstance(feature, NumericFeature):
        _get_values = get_values(s)
        if _get_values:
            return _get_values
        return range(get_min_value(s), get_max_value(s) + 1)[:10]

    return None


output = {}
for feature in fm:
    name = feature.name.str()
    option = feature.output_string.str()
    numeric_values = get_numeric_values(feature)
    if numeric_values:
        output[name] = [f"{option}{i}" for i in numeric_values]
    else:
        output[name] = option

print(json.dumps(output))
