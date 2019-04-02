"""
The PaperConfig pins down a specific set of case studies that can be reproduced
automatically.
"""

from pathlib import Path

import yaml

import varats.paper.case_study
from varats.settings import CFG


class PaperConfig():
    """
    Paper config to specify a set of case studies for a publication.

    The paper config allows easy reevaluation of a set of case studies.
    """

    def __init__(self, folder_path):
        self.__path = Path(folder_path)
        self.__case_studies = dict()
        for case_study_file in \
                [x for x in self.__path.iterdir()
                 if x.suffix == ".case_study"]:
            with open(case_study_file, "r") as cs_file:
                case_study = yaml.safe_load(cs_file)
                self.__case_studies[case_study.project_name] = case_study

    def get_case_study(self, cs_name):
        """
        Return case study with name `cs_name`.
        """
        return self.__case_studies[cs_name]

    def has_case_study(self, cs_name):
        """
        Check if a case study with `cs_name` was loaded.
        """
        return cs_name in self.__case_studies.keys()

    def get_filter_for_case_study(self, cs_name):
        """
        Return case study specific version filter.
        """
        if self.has_case_study(cs_name):
            return self.get_case_study(cs_name).get_version_filter()

        return lambda x: False

    def add_case_study(self, case_study):
        """
        Add a new case study to this paper config.
        """
        self.__case_studies[case_study.project_name] = case_study

    def store(self):
        """
        Persist the current state of the paper config.
        """
        for case_study in self.__case_studies.values():
            with open(self.__path / str(case_study.project_name +
                                        ".case_study"), "w") as cs_file:
                cs_file.write(yaml.dump(case_study))

    def __str__(self):
        string = "Loaded case studies:\n"
        for case_study in self.__case_studies.values():
            string += case_study.project_name
        return string


def project_filter_generator(project_name):
    """
    Generate project specific version filters.
    - if no paper config is loaded, we allow all versions
    - otherwise the paper config generates a specific version filter
    """
    if CFG["paper_config"]["current_config"].value is None:
        return lambda x: True

    if not is_paper_config_loaded():
        load_paper_config(str(CFG["paper_config"]["folder"]) + "/" +
                          str(CFG["paper_config"]["current_config"]))

    return get_paper_config().get_filter_for_case_study(project_name)


def get_paper_config() -> PaperConfig:
    """
    Returns the current paper config or None.
    """
    return __G_PAPER_CONFIG


def is_paper_config_loaded() -> bool:
    """
    Check if a currently a paper config is loaded.
    """
    return __G_PAPER_CONFIG is not None


def load_paper_config(config_path):
    """
    Load a paper config from yaml file.
    """
    global __G_PAPER_CONFIG
    __G_PAPER_CONFIG = PaperConfig(config_path)


__G_PAPER_CONFIG = None
