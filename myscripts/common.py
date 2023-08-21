import vara_feature.feature_model as FM


def load_feature_model(path):
    fm = FM.loadFeatureModel(path)
    if fm is None:
        raise ValueError("Feature Model could not be loaded!")
    return fm
