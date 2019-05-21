"""
A case study to pin down project settings and the exact set of revisions that
should be analysed.
"""

import yaml
from enum import Enum

from numpy import random
from scipy.stats import halfnorm

from varats.data.revisions import get_proccessed_revisions


class HashIDTuple(yaml.YAMLObject):
    """
    Combining a commit hash with a unique and ordered id, starting with 0 for
    the first commit in the repository.
    """

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
    """
    A case study persists a set of configuration values for a project to allow
    easy reevaluation.

    Stored values:
     - name of the related benchbuild.project
     - a set of revisions
    """

    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!CaseStudy'

    def __init__(self, project_name, version):
        self.__project_name = project_name
        self.__version = version
        self.__revisions = []

    @property
    def project_name(self):
        """
        Name of the related project.
        !! This name must match the name of the BB project !!
        """
        return self.__project_name

    @property
    def version(self):
        """
        Version ID for this case study.
        """
        return self.__version

    @property
    def revisions(self):
        """
        Project revisions that are part of this case study.
        """
        return [x.commit_hash for x in self.__revisions]

    def has_revision(self, revision: str):
        """
        Check if a revision is part of this case study.
        """
        for cs_revision in self.__revisions:
            if cs_revision.commit_hash.startswith(revision):
                return True

        return False

    def include_revision(self, revision, commit_id):
        """
        Add a revision to this case study.
        """
        if not self.has_revision(revision):
            self.__revisions.append(HashIDTuple(revision, commit_id))

    def include_revisions(self, revisions: [(str, int)]):
        """
        Add multiple revisions to this case study.

        Args:
            revisions: List of tuples with commit_hash and id
        """
        for revision in revisions:
            self.include_revision(revision[0], revision[1])

    def get_revision_filter(self):
        """
        Generate a case study specific revision filter that only allows
        revision that are part of the case study.
        """

        def revision_filter(revision):
            return self.has_revision(revision)

        return revision_filter

    def processed_revisions(self, result_file_type) -> [str]:
        """
        Calculate how many revisions were processed.
        """
        total_processed_revisions = set(
            get_proccessed_revisions(self.project_name, result_file_type))

        return [
            rev for rev in self.revisions
            if rev[:10] in total_processed_revisions
        ]

    def get_revisions_status(self, result_file_type) -> [(str, str)]:
        """
        Get status of all revisions.
        """
        processed_revisions = self.processed_revisions(result_file_type)
        return [(rev[:10], "OK" if rev in processed_revisions else "Missing")
                for rev in self.revisions]


###############################################################################
# Case study generation
###############################################################################


class SamplingMethod(Enum):
    """
    Enum for all currently supported sampling methods.
    """

    uniform = 1
    half_norm = 2


def generate_case_study(sampling_method: SamplingMethod, num_samples: int,
                        cmap, project_name: str, case_study_version: int,
                        extra_revisions: [str]) -> CaseStudy:
    """
    Generate a case study for a given project.

    This function will draw `num_samples` revisions from the history of the
    given project and persists the selected set into a case study for
    evaluation.
    """
    case_study = CaseStudy(project_name, case_study_version)
    # Needs to be sorted so the propability distribution over the length
    # of the list is the same as the distribution over the commits age history
    items = sorted([x for x in cmap.mapping_items()], key=lambda x: x[1])

    selected_items = [
        rev_item for rev_item in items if rev_item[0][:10] in extra_revisions
    ]

    filtered_items = [
        rev_item for rev_item in items if rev_item not in selected_items
    ]

    if sampling_method == SamplingMethod.half_norm:
        print("Using half-normal distribution")
        probabilities = halfnorm.rvs(scale=1, size=len(filtered_items))
    elif sampling_method == SamplingMethod.uniform:
        print("Using uniform distribution")
        probabilities = random.uniform(0, 1.0, len(filtered_items))

    probabilities /= probabilities.sum()
    filtered_idxs = random.choice(
        len(filtered_items), num_samples, p=probabilities)

    for idx in filtered_idxs:
        selected_items.append(filtered_items[idx])

    for item in sorted(selected_items, key=lambda x: x[1], reverse=True):
        case_study.include_revision(item[0], item[1])

    return case_study


def store_case_study(case_study: CaseStudy, paper_path: str):
    """
    Store case study to file.
    """
    file_name = "{project_name}_{version}.case_study".format(
        project_name=case_study.project_name, version=case_study.version)
    with open(paper_path / file_name, "w") as cs_file:
        cs_file.write(yaml.dump(case_study))
