import signal

import vara_feature.feature_model as FM
from vara_feature.configuration import getAllConfigs


def getConfigs(fm):
    signal.alarm(180)
    allConfigs = getAllConfigs(fm)
    signal.alarm(0)
    configs = []
    for config in allConfigs:
        options = dict()
        #for option in config:
        for option in config.getOptions():
            name = option.name
            value: str = option.value
            if value == "true":
                options[name] = True
            elif value == "false":
                options[name] = False
            elif value.isdigit():
                options[name] = int(value)
            else:
                options[name] = value
        if options not in configs:
            # Reduce number of duplicates caused by buggy getAllCondfigs
            configs.append(options)
    return reversed(configs)


def load_feature_model(path):
    fm = FM.loadFeatureModel(path)
    if fm is None:
        raise ValueError("Feature Model could not be loaded!")
    return fm


def remove_empty(dictionary):
    return dict(filter(lambda item: item[0], dictionary.items()))


def remove_false(dictionary):
    return dict(
        filter(
            lambda item: item[1] or type(item[1]) is int, dictionary.items()
        )
    )


def replace_feature_with_option(config, feature_to_options):
    out = {}
    for key, value in config.items():
        option = feature_to_options[key]
        if isinstance(value, bool):
            pass
        elif isinstance(value, int):
            tmp = list(filter(lambda o: str(value) in o, option))
            assert len(tmp) == 1
            option = tmp[0]
        else:
            raise NotImplementedError()

        out[option] = value
    return out


def config_to_options(config, feature_to_options):
    return list(
        remove_empty(
            remove_false(
                replace_feature_with_option(config, feature_to_options)
            )
        )
    )
