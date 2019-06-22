"""
The PaperConfig pins down a specific set of case studies that can be reproduced
automatically.
"""

from pathlib import Path

import yaml

from varats.paper.case_study import load_case_study_from_file
from varats.settings import CFG


class PaperConfig():
    """
    Paper config to specify a set of case studies for a publication.

    The paper config allows easy reevaluation of a set of case studies.
    """

    def __init__(self, folder_path):
        self.__path = Path(folder_path)
        self.__case_studies = dict()
        for case_study_path in \
                [x for x in self.__path.iterdir()
                 if x.suffix == ".case_study"]:
            case_study = load_case_study_from_file(case_study_path)
            if case_study.project_name in self.__case_studies.keys():
                self.__case_studies[case_study.project_name].append(case_study)
            else:
                self.__case_studies[case_study.project_name] = [case_study]

    def get_case_studies(self, cs_name):
        """
        Return case studies with project name `cs_name`.
        """
        return self.__case_studies[cs_name]

    def get_all_case_studies(self):
        """
        Returns a full list of all case studies with all different version.
        """
        return [
            case_study for case_study_list in self.__case_studies.values()
            for case_study in case_study_list
        ]

    def has_case_study(self, cs_name):
        """
        Check if a case study with `cs_name` was loaded.
        """
        return cs_name in self.__case_studies.keys()

    def get_filter_for_case_study(self, cs_name):
        """
        Return case study specific revision filter.
        If a one case study includes a revision it should be considered.

        Returns: True if a revision should be considered, False if it should
                 be filtered.
        """
        if self.has_case_study(cs_name):
            rev_filters = [
                cs.get_revision_filter()
                for cs in self.get_case_studies(cs_name)
            ]

            def multi_case_study_rev_filter(revision):
                for rev_filter in rev_filters:
                    if rev_filter(revision):
                        return True
                return False

            return multi_case_study_rev_filter

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
            with open(
                    self.__path / str(case_study.project_name + ".case_study"),
                    "w") as cs_file:
                cs_file.write(yaml.dump(case_study))

    def __str__(self):
        string = "Loaded case studies:\n"
        for case_study in self.__case_studies.values():
            string += case_study.project_name
        return string


def project_filter_generator(project_name):
    """
    Generate project specific revision filters.
    - if no paper config is loaded, we allow all revisions
    - otherwise the paper config generates a specific revision filter
    """
    if CFG["paper_config"]["current_config"].value is None:
        return lambda x: True

    if not is_paper_config_loaded():
        load_paper_config(
            str(CFG["paper_config"]["folder"]) + "/" +
            str(CFG["paper_config"]["current_config"]))

    return get_paper_config().get_filter_for_case_study(project_name)


def get_paper_config() -> PaperConfig:
    """
    Returns the current paper config or None.
    """
    if __G_PAPER_CONFIG is None:
        raise Exception('Paper config was not loaded')
    return __G_PAPER_CONFIG


def is_paper_config_loaded() -> bool:
    """
    Check if a currently a paper config is loaded.
    """
    return __G_PAPER_CONFIG is not None


def load_paper_config(config_path=None):
    """
    Load a paper config from yaml file.
    """
    if config_path is None:
        config_path = (str(CFG["paper_config"]["folder"]) +
                       "/" + str(CFG["paper_config"]["current_config"]))

    global __G_PAPER_CONFIG
    __G_PAPER_CONFIG = PaperConfig(config_path)


__G_PAPER_CONFIG = None
