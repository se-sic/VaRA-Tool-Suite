#!/usr/bin/env python3
import json
from sys import argv

import vara_feature.feature_model as FM

fm = FM.loadFeatureModel(argv[1])

output = {}
for feature in fm:
    name = feature.name.str()
    option = feature.output_string.str()

    output[name] = option

print(json.dumps(output))
