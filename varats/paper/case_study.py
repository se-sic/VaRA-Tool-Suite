"""
A case study to pin down project settings and the exact set of revisions that
should be analysed.
"""

from enum import Enum
from pathlib import Path
import errno
import os
import yaml

from numpy import random
from scipy.stats import halfnorm

from varats.data.revisions import get_proccessed_revisions
from varats.plots.plot_utils import check_required_args


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


class CSStage(yaml.YAMLObject):
    """
    A stage in a case-study, i.e., a collection of revisions. Stages are used
    to separate revisions into groups.
    """

    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!CSStage'

    def __init__(self):
        self.__revisions = []

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

    def add_revision(self, revision: str, commit_id):
        """
        Add a new revision to this stage.
        """
        if not self.has_revision(revision):
            self.__revisions.append(HashIDTuple(revision, commit_id))

    def sort(self, reverse=True):
        """
        Sort revisions by commit id.
        """
        self.__revisions.sort(key=lambda x: x.commit_id, reverse=reverse)


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
        self.__stages = []

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
        return [x for stage in self.__stages for x in stage.revisions]

    @property
    def stages(self):
        """
        Get a list with all stages.
        """
        # Return new list to forbid modification of the case-study
        return [stage for stage in self.__stages]

    @property
    def num_stages(self):
        """
        Get nummer of stages.
        """
        return len(self.__stages)

    def has_revision(self, revision: str):
        """
        Check if a revision is part of this case study.
        """
        for stage in self.__stages:
            if stage.has_revision(revision):
                return True

        return False

    def include_revision(self,
                         revision,
                         commit_id,
                         stage_num=0,
                         sort_revs=True):
        """
        Add a revision to this case study.
        """
        # Create missing stages
        while len(self.__stages) <= stage_num:
            self.__stages.append(CSStage())

        stage = self.__stages[stage_num]

        if not stage.has_revision(revision):
            stage.add_revision(revision, commit_id)
            if sort_revs:
                stage.sort()

    def include_revisions(self,
                          revisions: [(str, int)],
                          stage_num=0,
                          sort_revs=True):
        """
        Add multiple revisions to this case study.

        Args:
            stage: The stage to insert the revisions
            revisions: List of triples with (commit_hash, id) to be inserted
            sort_revs: True if the stage should be kept sorted
        """
        for revision in revisions:
            self.include_revision(revision[0], revision[1], stage_num, False)

        if sort_revs:
            self.__stages[stage_num].sort()

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


def load_case_study_from_file(file_path: Path) -> CaseStudy:
    """
    Load a case-study from a file.
    """
    if file_path.exists():
        with open(file_path, "r") as cs_file:
            return yaml.safe_load(cs_file)

    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                            str(file_path))


def store_case_study(case_study: CaseStudy, case_study_location: Path):
    """
    Store case study to file in the specified paper_config.

    Args:
        case_study_location: can be either a path to a paper_config
                                or a direct path to a `.case_study` file
    """
    if case_study_location.suffix == '.case_study':
        __store_case_study_to_file(case_study, case_study_location)
    else:
        __store_case_study_to_paper_config(case_study, case_study_location)


def __store_case_study_to_paper_config(case_study: CaseStudy,
                                       paper_config_path: Path):
    """
    Store case study to file in the specified paper_config.
    """
    file_name = "{project_name}_{version}.case_study".format(
        project_name=case_study.project_name, version=case_study.version)
    __store_case_study_to_file(case_study, paper_config_path / file_name)


def __store_case_study_to_file(case_study: CaseStudy, file_path: Path):
    """
    Store case study to file.
    """
    with open(file_path, "w") as cs_file:
        cs_file.write(yaml.dump(case_study))


###############################################################################
# Case study generation
###############################################################################


class SamplingMethod(Enum):
    """
    Enum for all currently supported sampling methods.
    """

    uniform = 1
    half_norm = 2


@check_required_args(['extra_revs'])
def generate_case_study(sampling_method: SamplingMethod, num_samples: int,
                        cmap, project_name: str, case_study_version: int,
                        **kwargs) -> CaseStudy:
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
        rev_item for rev_item in items
        if rev_item[0][:10] in kwargs['extra_revs']
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

    case_study.include_revisions(selected_items, sort_revs=True)

    return case_study


###############################################################################
# Case study extender
###############################################################################


class ExtenderStrategy(Enum):
    """
    Enum for all currently supported extender strategies.
    """

    simple_add = 1


@check_required_args(['strategy'])
def extend_case_study(case_study: CaseStudy, cmap, **kwargs) -> CaseStudy:
    """
    TODO: comment
    """
    """
    Needs:
        extender strat
            -> distribution
        num revs
        posible: list of extra revs = extra_revs
        current case study = case_study
    """

    if kwargs['strategy'] is ExtenderStrategy.simple_add:
        extend_with_extra_revs(case_study, cmap, **kwargs)

    print(case_study)


@check_required_args(['extra_revs', 'merge_stage'])
def extend_with_extra_revs(case_study: CaseStudy, cmap, **kwargs):
    """
    Extend a case_study with extra revisions.
    """
    extra_revs = kwargs['extra_revs']
    print(extra_revs)
    merge_stage = kwargs['merge_stage']

    # If no merge_stage was specified add it to the last
    if merge_stage == -1:
        merge_stage = case_study.num_stages - 1

    new_rev_items = []

    case_study.include_revisions(new_rev_items, merge_stage, True)
