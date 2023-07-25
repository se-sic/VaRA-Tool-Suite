#!/usr/bin/env python3
from sys import argv

from more_itertools import powerset

available_options = argv[1:]
id = 0

output = {}
for combination in powerset(available_options):
    options = []
    for option in combination:
        options.append(f'"{option}"')
    output[id] = f"""'[{', '.join(options)}]'"""
    id += 1

for id in output:
    print(f"    - {id}")

mapping = []
for id, config in output.items():
    mapping.append(f"{id}: {config}")

print(f"""...
---
{chr(10).join(mapping)}
...
""")
