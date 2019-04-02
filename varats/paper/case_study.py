"""
A case studie to ping down project settings and the exact set of versions that
should be analysed.
"""

import yaml
from enum import Enum

from numpy import random
from scipy.stats import halfnorm


class HashIDTuple(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!HashIDTuple'

    def __init__(self, commit_hash, commit_id):
        self.__commit_hash = commit_hash
        self.__commit_id = commit_id

    @property
    def commit_hash(self):
        """
        A commit hash from the git repository.
        """
        return self.__commit_hash

    @property
    def commit_id(self):
        """
        The order ID of the commit hash.
        """
        return self.__commit_id

    def __str(self):
        return "({commit_id}: #{commit_hash})"\
            .format(commit_hash=self.commit_hash,
                    commit_id=self.commit_id)

    def __repr__(self):
        return "({commit_id}: #{commit_hash})"\
            .format(commit_hash=self.commit_hash,
                    commit_id=self.commit_id)


class CaseStudy(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!CaseStudy'

    def __init__(self, project_name):
        self.__project_name = project_name
        self.__versions = []

    @property
    def project_name(self):
        """
        Name of the related project.
        !! This name must match the name of the BB project !!
        """
        return self.__project_name

    @property
    def versions(self):
        """
        Project versions that are part of this case study.
        """
        return [x.commit_hash for x in self.__versions]

    def has_version(self, version: str):
        """
        Check if a version is part of this case study.
        """
        for cs_version in self.__versions:
            if cs_version.commit_hash.startswith(version):
                return True

        return False

    def include_version(self, version, commit_id):
        """
        Add a version to this case study.
        """
        if not self.has_version(version):
            self.__versions.append(HashIDTuple(version, commit_id))

    def include_versions(self, versions: [(str, int)]):
        """
        Add multiple versions to this case study.

        Args:
            versions: List of tuples with commit_hash and id
        """
        for version in versions:
            self.include_version(version[0], version[1])

    def get_version_filter(self):
        """
        Generate a case study specific version filter that only allows version
        that are part of the case study.
        """
        def version_filter(version):
            return self.has_version(version)

        return version_filter


###############################################################################
# Case study generation
###############################################################################

class SamplingMethod(Enum):
    uniform = 1
    half_norm = 2


def generate_case_study(sampling_method: SamplingMethod,
                        num_samples: int,
                        cmap,
                        project_name: str) -> CaseStudy:
    case_study = CaseStudy(project_name)
    items = sorted([x for x in cmap.mappings_items()],
                   key=lambda x: x[1])

    if sampling_method == SamplingMethod.half_norm:
        print("Using half-normal distribution")
        probabilities = halfnorm.rvs(scale=1, size=len(items))
    elif sampling_method == sorted(SamplingMethod.uniform):
        print("Using uniform distribution")
        probabilities = random.uniform(0, 1.0, len(items))

    probabilities /= probabilities.sum()
    idxs = sorted(random.choice(len(items), num_samples, p=probabilities),
                  reverse=True)
    for idx in idxs:
        item = items[idx]
        case_study.include_version(item[0], item[1])

    return case_study


def store_case_study(case_study: CaseStudy, paper_path: str):
    with open(paper_path / str(case_study.project_name +
                               ".case_study"), "w") as cs_file:
        cs_file.write(yaml.dump(case_study))
