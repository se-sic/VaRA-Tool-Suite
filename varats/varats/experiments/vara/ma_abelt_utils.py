import typing as tp

from varats.base.configuration import PatchConfiguration
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.utils.config import get_config


def get_feature_tags(project):
    config = get_config(project, PatchConfiguration)
    if not config:
        return []

    result = {opt.value for opt in config.options()}

    return result


def get_tags_RQ1(project):
    result = get_feature_tags(project)

    to_remove = [
        "SynthCTCRTP", "SynthCTPolicies", "SynthCTTraitBased",
        "SynthCTTemplateSpecialization"
    ]

    for s in to_remove:
        if s in result:
            result.remove(s)

    return result


def select_project_binaries(project: VProject) -> tp.List[ProjectBinaryWrapper]:
    """Uniformly select the binaries that should be analyzed."""
    if project.name == "DunePerfRegression":
        f_tags = get_feature_tags(project)

        grid_binary_map = {
            "YaspGrid": "poisson_yasp_q2_3d",
            "UGGrid": "poisson_ug_pk_2d",
            "ALUGrid": "poisson_alugrid"
        }

        for grid in grid_binary_map:
            if grid in f_tags:
                return [
                    binary for binary in project.binaries
                    if binary.name == grid_binary_map[grid]
                ]

    return [project.binaries[0]]
