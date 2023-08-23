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
        configs.append(options)
    return reversed(configs)


def load_feature_model(path):
    fm = FM.loadFeatureModel(path)
    if fm is None:
        raise ValueError("Feature Model could not be loaded!")
    return fm


def config_to_options(config, feature_to_options):
    options = []
    for key, value in config.items():
        option = feature_to_options[key]
        print(key, value, option)
        if option:
            if isinstance(value, bool):
                if value:
                    options.append(option)
            elif isinstance(value, int):
                option = list(filter(lambda o: str(value) in o, option))
                assert len(option) == 1
                options.append(option[0])
            else:
                raise NotImplementedError()
    return options
