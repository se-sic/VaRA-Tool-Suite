"""
A case study to pin down project settings and the exact set of revisions that
should be analysed.
"""

import typing as tp
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
import errno
import os
import random
import yaml

from scipy.stats import halfnorm
import numpy as np
import pygit2

from varats.data.revisions import get_proccessed_revisions, get_failed_revisions
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
    def commit_hash(self) -> str:
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
        return list(
            dict.fromkeys(
                [x for stage in self.__stages for x in stage.revisions]))

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

    def has_revision(self, revision: str) -> bool:
        """
        Check if a revision is part of this case study.
        """
        for stage in self.__stages:
            if stage.has_revision(revision):
                return True

        return False

    def has_revision_in_stage(self, revision: str, num_stage) -> bool:
        """
        Check if a revision of a specific stage.
        """
        if self.num_stages <= num_stage:
            return False
        return self.__stages[num_stage].has_revision(revision)

    def include_revision(self,
                         revision,
                         commit_id,
                         stage_num=0,
                         sort_revs=True):
        """
        Add a revision to this case study.
        """
        # Create missing stages
        while self.num_stages <= stage_num:
            self.__stages.append(CSStage())

        stage = self.__stages[stage_num]

        if not stage.has_revision(revision):
            stage.add_revision(revision, commit_id)
            if sort_revs:
                stage.sort()

    def include_revisions(self,
                          revisions: tp.List[tp.Tuple[str, int]],
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

        if sort_revs and self.num_stages > 0:
            self.__stages[stage_num].sort()

    def get_revision_filter(self):
        """
        Generate a case study specific revision filter that only allows
        revision that are part of the case study.
        """

        def revision_filter(revision):
            return self.has_revision(revision)

        return revision_filter

    def processed_revisions(self, result_file_type) -> tp.List[str]:
        """
        Calculate how many revisions were processed.
        """
        total_processed_revisions = set(
            get_proccessed_revisions(self.project_name, result_file_type))

        return [
            rev for rev in self.revisions
            if rev[:10] in total_processed_revisions
        ]

    def failed_revisions(self, result_file_type) -> tp.List[str]:
        """
        Calculate which revisions failed.
        """
        total_failed_revisions = set(
            get_failed_revisions(self.project_name, result_file_type))

        return [
            rev for rev in self.revisions
            if rev[:10] in total_failed_revisions
        ]

    def get_revisions_status(self, result_file_type,
                             stage_num=-1) -> tp.List[tp.Tuple[str, str]]:
        """
        Get status of all revisions.
        """
        processed_revisions = self.processed_revisions(result_file_type)
        failed_revisions = self.failed_revisions(result_file_type)
        revisions_status = [
            (rev[:10], "OK" if rev in processed_revisions else
             "Failed" if rev in failed_revisions else "Missing")
            for rev in self.revisions
        ]
        if stage_num == -1:
            return revisions_status

        if stage_num < self.num_stages:
            stage = self.__stages[stage_num]
            return [x for x in revisions_status if stage.has_revision(x[0])]

        return []


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
# Case-study generation
###############################################################################


class SamplingMethod(Enum):
    """
    Enum for all currently supported sampling methods.
    """

    uniform = 1
    half_norm = 2

    def gen_distribution_function(self):
        """
        Generate a distribution function for the specified sampling method.
        """
        if self == SamplingMethod.uniform:

            def uniform(num_samples):
                return np.random.uniform(0, 1.0, num_samples)

            return uniform
        if self == SamplingMethod.half_norm:

            def halfnormal(num_samples):
                return halfnorm.rvs(scale=1, size=num_samples)

            return halfnormal

        raise Exception('Unsupported SamplingMethod')


@check_required_args(['extra_revs', 'git_path', 'revs_per_year'])
def generate_case_study(sampling_method: SamplingMethod, num_samples: int,
                        cmap, case_study_version: int, project_name: str,
                        **kwargs) -> CaseStudy:
    """
    Generate a case study for a given project.

    This function will draw `num_samples` revisions from the history of the
    given project and persists the selected set into a case study for
    evaluation.
    """
    case_study = CaseStudy(project_name, case_study_version)

    if kwargs['extra_revs']:
        extend_with_extra_revs(case_study, cmap, **kwargs)

    if kwargs['revs_per_year'] > 0:
        extend_with_revs_per_year(case_study, cmap, **kwargs)

    extend_with_distrib_sampling(case_study, cmap, **kwargs)

    return case_study


###############################################################################
# Case-study extender
###############################################################################


class ExtenderStrategy(Enum):
    """
    Enum for all currently supported extender strategies.
    """

    simple_add = 1
    distrib_add = 2
    smooth_plot = 3
    per_year_add = 4


def extend_case_study(case_study: CaseStudy, cmap,
                      ext_strategy: ExtenderStrategy, **kwargs):
    """
    Extend a case study with new revisions.
    """

    if ext_strategy is ExtenderStrategy.simple_add:
        extend_with_extra_revs(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.distrib_add:
        extend_with_distrib_sampling(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.smooth_plot:
        extend_with_smooth_revs(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.per_year_add:
        extend_with_revs_per_year(case_study, cmap, **kwargs)


@check_required_args(['extra_revs', 'merge_stage'])
def extend_with_extra_revs(case_study: CaseStudy, cmap, **kwargs):
    """
    Extend a case_study with extra revisions.
    """
    extra_revs = kwargs['extra_revs']
    merge_stage = kwargs['merge_stage']

    new_rev_items = [
        rev_item for rev_item in cmap.mapping_items()
        if any(map(rev_item[0].startswith, extra_revs))
    ]

    case_study.include_revisions(new_rev_items, merge_stage, True)


@check_required_args(['git_path', 'revs_per_year', 'merge_stage'])
def extend_with_revs_per_year(case_study: CaseStudy, cmap, **kwargs):
    """
    Extend a case_study with n revisions per year.
    """
    repo_path = pygit2.discover_repository(kwargs['git_path'])
    repo = pygit2.Repository(repo_path)
    last_commit = repo[repo.head.target]

    commits = defaultdict(list) # maps year -> list of commits
    for commit in repo.walk(last_commit.id, pygit2.GIT_SORT_TIME):
        commit_date = datetime.utcfromtimestamp(commit.commit_time)
        commits[commit_date.year].append(str(commit.id))

    new_rev_items = [] # new revisions that get added to to case_study
    for _, commits_in_year in commits.items():
        samples = min(len(commits_in_year), kwargs['revs_per_year'])
        sample_commit_indices = sorted(random.sample(range(len(commits_in_year)), samples))

        for commit_index in sample_commit_indices:
            commit_hash = commits_in_year[commit_index]
            time_id = cmap.time_id(commit_hash)
            new_rev_items.append((commit_hash, time_id))

    case_study.include_revisions(new_rev_items, kwargs['merge_stage'], True)


@check_required_args(['distribution', 'merge_stage', 'num_rev'])
def extend_with_distrib_sampling(case_study: CaseStudy, cmap, **kwargs):
    """
    Extend a case study by sampling `num_rev` new revisions.
    """
    # Needs to be sorted so the propability distribution over the length
    # of the list is the same as the distribution over the commits age history
    revision_list = [
        rev_item for rev_item in sorted([x for x in cmap.mapping_items()],
                                        key=lambda x: x[1]) if not case_study.
        has_revision_in_stage(rev_item[0], kwargs['merge_stage'])
    ]

    distribution_function = kwargs['distribution'].gen_distribution_function()

    case_study.include_revisions(
        sample_n_idxs(distribution_function, kwargs['num_rev'], revision_list),
        kwargs['merge_stage'])


def sample_n_idxs(distrib_func, num_samples,
                  list_to_sample: tp.List) -> tp.List:
    """
    Args:
        distrib_func: Distribution function with
                        f(n) -> [] where len([]) == n probabilities
        num_samples: number of samples to choose
        list_to_sample: list to sample from

    Returns:
        list[] of sampled items
    """
    probabilities = distrib_func(len(list_to_sample))
    probabilities /= probabilities.sum()

    sampled_idxs = np.random.choice(
        len(list_to_sample), num_samples, p=probabilities)

    return [list_to_sample[idx] for idx in sampled_idxs]


@check_required_args(['plot_type', 'boundary_gradient'])
def extend_with_smooth_revs(case_study: CaseStudy, cmap, **kwargs):
    """
    Extend a case study with extra revisions that could smooth plot curves.
    This can remove steep gradients that result from missing certain revisions
    when sampling.
    """
    plot_type = kwargs['plot_type'].type

    kwargs['plot_case_study'] = case_study
    kwargs['cmap'] = cmap
    plot = plot_type(**kwargs)
    # convert input to float %
    boundary_gradient = kwargs['boundary_gradient'] / float(100)
    print("Using boundary gradient: ", boundary_gradient)
    new_revisions = plot.calc_missing_revisions(boundary_gradient)

    print("Found new revisions: ", new_revisions)
    # Remove revision that are already present in another stage.
    new_revisions = [
        rev for rev in new_revisions if not case_study.has_revision(rev)
    ]
    case_study.include_revisions([(rev, cmap.time_id(rev))
                                  for rev in new_revisions],
                                 kwargs['merge_stage'])
