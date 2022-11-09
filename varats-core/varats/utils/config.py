"""Module for config specific utilities."""
import typing as tp
from pathlib import Path

from varats.base.configuration import Configuration
from varats.mapping.configuration_map import ConfigurationMap
from varats.paper.case_study import (
    CaseStudy,
    load_configuration_map_from_case_study_file,
)
from varats.paper.paper_config import PaperConfig


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
