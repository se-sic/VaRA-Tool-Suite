import typing as tp

import numpy as np

from varats.base.configuration import PatchVariationConfiguration
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_paper_config
from varats.project.patch_variation_source import get_current_variation_id
from varats.project.varats_project import VProject
from varats.utils.config import load_configuration_map_for_case_study

HIDDEN_CONFIG_REPS = 10


def get_variation_config(
    project: VProject
) -> tp.Optional[PatchVariationConfiguration]:
    # Get patch variation config
    variation_id = get_current_variation_id(project)
    if variation_id is None:
        return None

    paper_config = get_paper_config()
    case_studies = paper_config.get_case_studies(cs_name=project.name)

    if len(case_studies) > 1:
        raise AssertionError(
            "Cannot handle multiple case studies of the same project."
        )

    case_study = case_studies[0]

    config_map = load_configuration_map_for_case_study(
        paper_config, case_study, PatchVariationConfiguration
    )

    variation = config_map.get_configuration(variation_id)

    return variation


def get_variations_as_dict(
    project: VProject
) -> tp.Dict[str, tp.Dict[str, tp.Any]]:
    return {
        o.name: dict(o.value) for o in get_variation_config(project).options()
    }


def get_all_variations_as_dict(
    case_study: CaseStudy
) -> tp.Dict[str, tp.Tuple[str, tp.Any]]:
    paper_config = get_paper_config()

    config_map = load_configuration_map_for_case_study(
        paper_config, case_study, PatchVariationConfiguration
    )

    result: tp.Dict[str, tp.Tuple[str, tp.Any]] = {}

    for cid in config_map.ids():
        variation = config_map.get_configuration(cid)
        if variation is None:
            continue

        for o in variation.options():
            patch_name = o.name
            if len(o.value) > 1:
                print(
                    "Warning: Multiple arguments for patch variation, only the first one will be used."
                )

            for arg_name, arg_values in o.value.items():
                result[patch_name] = (
                    arg_name, list(arg_values) + sample_variations(arg_values)
                )

    return result


def sample_variations(values: tp.List[tp.Any],
                      num_samples: int = 20) -> tp.List[tp.Any]:
    rng = np.random.default_rng(seed=42)

    if isinstance(values[0], int):
        random_values = rng.integers(
            min(values), max(values) + 1, size=num_samples
        )
    elif isinstance(values[0], float):
        # We want to sample floats with the same number of decimal places as the provided values
        decimal_places = max([0] + [str(v)[::-1].find(".") for v in values])
        random_values = rng.uniform(min(values), max(values), size=num_samples)
        random_values = np.round(random_values, decimals=decimal_places)
    else:
        raise ValueError(
            f"Unsupported value type {type(values[0])} for during sampling"
        )

    # Erase duplicates from the random values and the provided values
    unique_values = set(values)
    unique_random_values = set(random_values)
    unique_random_values = unique_random_values - unique_values

    return list(unique_random_values)
