import typing as tp


def feature_region_string_from_set(feature_region_set: tp.Iterable[str]) -> str:
    """
    Convert a feature region set to a string representation.

    The string representation is a comma separated list of feature region names, enclosed by 'FR(' and ')'.
    @param feature_region_set: The feature region set to convert.
    @return: The string representation of the feature region set.
    """
    return "FR(" + ",".join(feature_region_set) + ")"


def extract_feature_region_set_from_string(
    feature_region_string: str
) -> tp.Set[str]:
    """
    Extract a feature region set from a string representation.

    The string representation is a comma separated list of feature region names, enclosed by 'FR(' and ')'.
    @param feature_region_string: The string representation of the feature region set.
    @return: The feature region set.
    """
    feature_region_string = feature_region_string.replace("FR", "").replace(
        "(", ""
    ).replace(")", "")
    return set(feature_region_string.split(","))
