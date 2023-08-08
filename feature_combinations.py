#!/usr/bin/env python3
from sys import argv

from more_itertools import powerset


def parse():
    actions = argv[1].split(";")
    options = argv[2:]

    return actions, options


def wrap_ticks(wrappee):
    return map(lambda x: f'"{x}"', wrappee)


def create_mapping(available_actions, available_options):
    id = 0
    mapping = {}

    for actions in powerset(available_actions):
        for options in powerset(available_options):
            mapping[id] = f"""'[{', '.join(wrap_ticks(actions + options))}]'"""
            id += 1

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
    actions, options = parse()
    mapping = create_mapping(actions, options)
    formatted_print(mapping)


if __name__ == "__main__":
    main()
