"""Module for config specific utilities."""
import typing as tp
from pathlib import Path

from varats.base.configuration import (
    Configuration,
    PlainCommandlineConfiguration,
    PatchConfiguration,
)
from varats.mapping.configuration_map import ConfigurationMap
from varats.paper.case_study import (
    CaseStudy,
    load_configuration_map_from_case_study_file,
)
from varats.paper.paper_config import PaperConfig, get_paper_config
from varats.project.sources import FeatureSource
from varats.provider.patch.patch_provider import PatchSet, PatchProvider
from varats.utils.git_util import ShortCommitHash

if tp.TYPE_CHECKING:
    from varats.project.varats_project import VProject


def load_configuration_map_for_case_study(
    paper_config: PaperConfig, case_study: CaseStudy,
    concrete_config_type: tp.Type[Configuration]
) -> ConfigurationMap:
    """
    Loads the \a ConfigurationMap attached to the specified \a CaseStudy. The
    configuration map is assumed to contain configurations of the type \a
    concrete_config_type.

    Args:
        paper_config: in which the case study is
        case_study: the case study to load the map for
        concrete_config_type: the type of configuration contained in the map

    Returns:
        map that contains all configurations used in the case study
    """
    return load_configuration_map_from_case_study_file(
        Path(
            paper_config.path /
            f"{case_study.project_name}_{case_study.version}.case_study"
        ), concrete_config_type
    )


def get_current_config_id(project: 'VProject') -> tp.Optional[int]:
    """
    Get, if available, the current config id of project. Should the project be
    not configuration specific ``None`` is returned.

    Args:
        project: to extract the config id from

    Returns:
        config_id if available for the given project
    """
    if project.active_revision.has_variant(FeatureSource.LOCAL_KEY):
        return int(
            project.active_revision.variant_by_name(FeatureSource.LOCAL_KEY
                                                   ).version
        )

    return None


def get_config(
    project: 'VProject', config_type: tp.Type[Configuration]
) -> tp.Optional[Configuration]:
    config_id = get_current_config_id(project)
    if config_id is None:
        return None

    paper_config = get_paper_config()
    case_studies = paper_config.get_case_studies(cs_name=project.name)

    if len(case_studies) > 1:
        raise AssertionError(
            "Cannot handle multiple case studies of the same project."
        )

    case_study = case_studies[0]

    config_map = load_configuration_map_for_case_study(
        paper_config, case_study, config_type
    )

    config = config_map.get_configuration(config_id)

    return config


def get_extra_config_options(project: 'VProject') -> tp.List[str]:
    """
    Get extra program options that were specified in the particular
    configuration of \a Project.

    Args:
        project: to get the extra options for

    Returns:
        list of command line options as string
    """
    config = get_config(project, PlainCommandlineConfiguration)
    if not config:
        return []
    return list(map(lambda option: option.value, config.options()))


def get_config_patches(project: 'VProject') -> PatchSet:
    """
    Get required patches for the particular configuration of \a Project.

    Args:
        project: to get the patches for

    Returns:
        list of patches
    """
    config = get_config(project, PatchConfiguration)
    if not config:
        return PatchSet(set())

    patch_provider = PatchProvider.create_provider_for_project(project)
    revision = ShortCommitHash(project.revision.primary.version)
    feature_tags = {opt.value for opt in config.options()}
    patches = patch_provider.get_patches_for_revision(revision).all_of_features(
        feature_tags
    )

    return patches
