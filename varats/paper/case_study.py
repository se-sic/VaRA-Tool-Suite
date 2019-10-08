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

from varats.data.revisions import (get_processed_revisions,
                                   get_failed_revisions, get_tagged_revisions)
from varats.plots.plot_utils import check_required_args
from varats.data.version_header import VersionHeader
from varats.data.reports.commit_report import CommitMap
from varats.data.report import MetaReport, FileStatusExtension


class HashIDTuple():
    """
    Combining a commit hash with a unique and ordered id, starting with 0 for
    the first commit in the repository.
    """
    def __init__(self, commit_hash: str, commit_id: int) -> None:
        self.__commit_hash = commit_hash
        self.__commit_id = commit_id

    @property
    def commit_hash(self) -> str:
        """
        A commit hash from the git repository.
        """
        return self.__commit_hash

    @property
    def commit_id(self) -> int:
        """
        The order ID of the commit hash.
        """
        return self.__commit_id

    def get_dict(self) -> tp.Dict[str, tp.Union[str, int]]:
        return dict(commit_hash=self.commit_hash, commit_id=self.commit_id)

    def __str(self) -> str:
        return "({commit_id}: #{commit_hash})"\
            .format(commit_hash=self.commit_hash,
                    commit_id=self.commit_id)

    def __repr__(self) -> str:
        return "({commit_id}: #{commit_hash})"\
            .format(commit_hash=self.commit_hash,
                    commit_id=self.commit_id)


class CSStage():
    """
    A stage in a case-study, i.e., a collection of revisions. Stages are used
    to separate revisions into groups.
    """
    def __init__(self,
                 name: tp.Optional[str] = None,
                 revisions: tp.List[HashIDTuple] = []) -> None:
        self.__revisions: tp.List[HashIDTuple] = revisions
        self.__name: tp.Optional[str] = name

    @property
    def revisions(self) -> tp.List[str]:
        """
        Project revisions that are part of this case study.
        """
        return [x.commit_hash for x in self.__revisions]

    @property
    def name(self) -> tp.Optional[str]:
        """
        Name of the stage.
        """
        return self.__name

    @name.setter
    def name(self, name: str) -> None:
        """
        Setter for the name of the stage.
        """
        self.__name = name

    def has_revision(self, revision: str) -> bool:
        """
        Check if a revision is part of this case study.
        """
        for cs_revision in self.__revisions:
            if cs_revision.commit_hash.startswith(revision):
                return True

        return False

    def add_revision(self, revision: str, commit_id: int) -> None:
        """
        Add a new revision to this stage.
        """
        if not self.has_revision(revision):
            self.__revisions.append(HashIDTuple(revision, commit_id))

    def sort(self, reverse: bool = True) -> None:
        """
        Sort revisions by commit id.
        """
        self.__revisions.sort(key=lambda x: x.commit_id, reverse=reverse)

    def get_dict(self) -> tp.Dict[
        str, tp.Union[str, tp.List[tp.Dict[str, tp.Union[str, int]]]]]:

        stage_dict: tp.Dict[str, tp.Union[
            str, tp.List[tp.Dict[str, tp.Union[str, int]]]]] = dict()
        if self.name is not None:
            stage_dict['project_name'] = self.name
        revision_list = [revision.get_dict() for revision in self.__revisions]
        if len(revision_list) > 0:
            stage_dict['revisions'] = revision_list
        return stage_dict


class CaseStudy():
    """
    A case study persists a set of configuration values for a project to allow
    easy reevaluation.

    Stored values:
     - name of the related benchbuild.project
     - a set of revisions
    """

    yaml_tag = u'!CaseStudy'

    def __init__(self,
                 project_name: str,
                 version: int,
                 stages: tp.List[CSStage] = []) -> None:
        self.__project_name = project_name
        self.__version = version
        self.__stages = stages

    @property
    def project_name(self) -> str:
        """
        Name of the related project.
        !! This name must match the name of the BB project !!
        """
        return self.__project_name

    @property
    def version(self) -> int:
        """
        Version ID for this case study.
        """
        return self.__version

    @property
    def revisions(self) -> tp.List[str]:
        """
        Project revisions that are part of this case study.
        """
        return list(
            dict.fromkeys(
                [x for stage in self.__stages for x in stage.revisions]))

    @property
    def stages(self) -> tp.List[CSStage]:
        """
        Get a list with all stages.
        """
        # Return new list to forbid modification of the case-study
        return [stage for stage in self.__stages]

    @property
    def num_stages(self) -> int:
        """
        Get nummer of stages.
        """
        return len(self.__stages)

    def get_stage_by_name(self, stage_name: str) -> tp.Optional[CSStage]:
        """
        Get a stage by its name.
        Since multiple stages can have the same name, the first matching stage is returned.
        """
        for stage in self.__stages:
            if stage.name == stage_name:
                return stage

        return None

    def get_stage_index_by_name(self, stage_name: str) -> tp.Optional[int]:
        """
        Get a stage's index by its name.
        Since multiple stages can have the same name, the first matching stage is returned.
        """
        for i in range(len(self.__stages)):
            if self.__stages[i].name == stage_name:
                return i

        return None

    def has_revision(self, revision: str) -> bool:
        """
        Check if a revision is part of this case study.
        """
        for stage in self.__stages:
            if stage.has_revision(revision):
                return True

        return False

    def has_revision_in_stage(self, revision: str, num_stage: int) -> bool:
        """
        Check if a revision of a specific stage.
        """
        if self.num_stages <= num_stage:
            return False
        return self.__stages[num_stage].has_revision(revision)

    def shift_stage(self, from_index: int, offset: int) -> None:
        """
        Shift a stage in the case-studie's stage list by an offset.
        Beware that shifts to the left (offset<0) will destroy stages.
        """
        if not (0 <= from_index < len(self.__stages)):
            raise AssertionError("from_index out of bounds")
        if (from_index + offset) < 0:
            raise AssertionError("Shifting out of bounds")

        if offset > 0:
            for _ in range(offset):
                self.__stages.insert(from_index, CSStage())

        if offset < 0:
            remove_index = from_index + offset
            for _ in range(abs(offset)):
                self.__stages.pop(remove_index)

    def insert_empty_stage(self, pos: int) -> CSStage:
        """
        Insert a new stage at the given index, shifting the list elements to the right.
        The newly created stage is returned.
        """
        new_stage = CSStage()
        self.__stages.insert(pos, new_stage)
        return new_stage

    def include_revision(self,
                         revision: str,
                         commit_id: int,
                         stage_num: int = 0,
                         sort_revs: bool = True) -> None:
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
                          stage_num: int = 0,
                          sort_revs: bool = True) -> None:
        """
        Add multiple revisions to this case study.

        Args:
            revisions: List of tuples with (commit_hash, id) to be inserted
            stage_num: The stage to insert the revisions
            sort_revs: True if the stage should be kept sorted
        """
        for revision in revisions:
            self.include_revision(revision[0], revision[1], stage_num, False)

        if sort_revs and self.num_stages > 0:
            self.__stages[stage_num].sort()

    def name_stage(self, stage_num: int, name: str) -> None:
        """
        Names an already existing stage.

        Args:
            stage_num: The number of the stage to name
            name: The new name of the stage
        """
        if stage_num < self.num_stages:
            self.__stages[stage_num].name = name

    def get_revision_filter(self) -> tp.Callable[[str], bool]:
        """
        Generate a case study specific revision filter that only allows
        revision that are part of the case study.
        """

        def revision_filter(revision: str) -> bool:
            return self.has_revision(revision)

        return revision_filter

    def processed_revisions(self,
                            result_file_type: MetaReport) -> tp.List[str]:
        """
        Calculate how many revisions were processed.
        """
        total_processed_revisions = set(
            get_processed_revisions(self.project_name, result_file_type))

        return [
            rev for rev in self.revisions
            if rev[:10] in total_processed_revisions
        ]

    def failed_revisions(self, result_file_type: MetaReport) -> tp.List[str]:
        """
        Calculate which revisions failed.
        """
        total_failed_revisions = set(
            get_failed_revisions(self.project_name, result_file_type))

        return [
            rev for rev in self.revisions
            if rev[:10] in total_failed_revisions
        ]

    def get_revisions_status(self,
                             result_file_type: MetaReport,
                             stage_num: int = -1
                             ) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
        """
        Get status of all revisions.
        """
        tagged_revisions = get_tagged_revisions(self.project_name,
                                                result_file_type)

        def filtered_tagged_revs(
                rev_provider: tp.Iterable[str]
        ) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
            filtered_revisions = []
            for rev in rev_provider:
                found = False
                for tagged_rev in tagged_revisions:
                    if rev[:10] == tagged_rev[0][:10]:
                        filtered_revisions.append(tagged_rev)
                        found = True
                        break
                if not found:
                    filtered_revisions.append((rev[:10],
                                               FileStatusExtension.Missing))
            return filtered_revisions

        if stage_num == -1:
            return filtered_tagged_revs(self.revisions)

        if stage_num < self.num_stages:
            stage = self.__stages[stage_num]
            return filtered_tagged_revs(stage.revisions)

        return []

    def get_dict(self) -> tp.Dict[str, tp.Union[str, int, tp.List[tp.Dict[
        str, tp.Union[str, tp.List[tp.Dict[str, tp.Union[str, int]]]]]]]]:

        return dict(project_name=self.project_name,
                    version=self.version,
                    stages=[stage.get_dict() for stage in self.stages])


def load_case_study_from_file(file_path: Path) -> CaseStudy:
    """
    Load a case-study from a file.
    """
    if file_path.exists():
        with open(file_path, "r") as cs_file:
            documents = yaml.load_all(cs_file, Loader=yaml.CLoader)
            version_header = VersionHeader(next(documents))
            version_header.raise_if_not_type("CaseStudy")
            version_header.raise_if_version_is_less_than(1)

            raw_case_study = next(documents)
            stages: tp.List[CSStage] = []
            for raw_stage in raw_case_study['CSStage']:
                hash_id_tuples: tp.List[HashIDTuple] = []
                for raw_hash_id_tuple in raw_stage['HashIDTuple']:
                    hash_id_tuples.append(
                        HashIDTuple(raw_hash_id_tuple['commit_hash'],
                                    raw_hash_id_tuple['commit_id']))
                stages.append(CSStage(raw_stage['name'], hash_id_tuples))

            return CaseStudy(raw_case_study['name'],
                             raw_case_study['version'],
                             stages)

    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                            str(file_path))


def store_case_study(case_study: CaseStudy, case_study_location: Path) -> None:
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
                                       paper_config_path: Path) -> None:
    """
    Store case study to file in the specified paper_config.
    """
    file_name = "{project_name}_{version}.case_study".format(
        project_name=case_study.project_name, version=case_study.version)
    __store_case_study_to_file(case_study, paper_config_path / file_name)


def __store_case_study_to_file(case_study: CaseStudy, file_path: Path) -> None:
    """
    Store case study to file.
    """
    with open(file_path, "w") as cs_file:
        version_header: VersionHeader = \
            VersionHeader.from_version_number('CaseStudy', 1)

        cs_file.write(yaml.dump_all([version_header, case_study.get_dict()]))


def get_newest_result_files_for_case_study(
        case_study: CaseStudy, result_dir: Path,
        report_type: MetaReport) -> tp.List[Path]:
    """
    Return all result files that belong to a given case study.
    For revision with multiple files, the newest file will be selected.
    """
    files_to_store: tp.Dict[str, Path] = dict()

    result_dir /= case_study.project_name
    if not result_dir.exists():
        return []

    for opt_res_file in result_dir.iterdir():
        if report_type.is_result_file(opt_res_file.name):
            commit_hash = report_type.get_commit_hash_from_result_file(
                opt_res_file.name)
            if case_study.has_revision(commit_hash):
                current_file = files_to_store.get(commit_hash, None)
                if current_file is None:
                    files_to_store[commit_hash] = opt_res_file
                else:
                    if (current_file.stat().st_mtime <
                            opt_res_file.stat().st_mtime):
                        files_to_store[commit_hash] = opt_res_file

    return [x for x in files_to_store.values()]

###############################################################################
# Case-study generation
###############################################################################


class SamplingMethod(Enum):
    """
    Enum for all currently supported sampling methods.
    """

    uniform = 1
    half_norm = 2

    def gen_distribution_function(self) -> tp.Callable[[int], np.ndarray]:
        """
        Generate a distribution function for the specified sampling method.
        """
        if self == SamplingMethod.uniform:

            def uniform(num_samples: int) -> np.ndarray:
                return tp.cast(tp.List[float],
                               np.random.uniform(0, 1.0, num_samples))

            return uniform
        if self == SamplingMethod.half_norm:

            def halfnormal(num_samples: int) -> np.ndarray:
                return tp.cast(tp.List[float],
                               halfnorm.rvs(scale=1, size=num_samples))

            return halfnormal

        raise Exception('Unsupported SamplingMethod')


@check_required_args(['extra_revs', 'git_path'])
def generate_case_study(sampling_method: SamplingMethod, cmap: CommitMap,
                        case_study_version: int, project_name: str,
                        **kwargs: tp.Any) -> CaseStudy:
    """
    Generate a case study for a given project.

    This function will draw `num_samples` revisions from the history of the
    given project and persists the selected set into a case study for
    evaluation.
    """
    case_study = CaseStudy(project_name, case_study_version)

    if kwargs['revs_per_year'] > 0:
        extend_with_revs_per_year(case_study, cmap, **kwargs)

    if (sampling_method is SamplingMethod.half_norm
            or sampling_method is SamplingMethod.uniform):
        extend_with_distrib_sampling(case_study, cmap, **kwargs)

    if kwargs['extra_revs']:
        extend_with_extra_revs(case_study, cmap, **kwargs)

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


def extend_case_study(case_study: CaseStudy, cmap: CommitMap,
                      ext_strategy: ExtenderStrategy,
                      **kwargs: tp.Any) -> None:
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
def extend_with_extra_revs(case_study: CaseStudy, cmap: CommitMap,
                           **kwargs: tp.Any) -> None:
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


@check_required_args(['git_path', 'revs_per_year', 'merge_stage', 'revs_year_sep'])
def extend_with_revs_per_year(case_study: CaseStudy, cmap: CommitMap,
                              **kwargs: tp.Any) -> None:
    """
    Extend a case_study with n revisions per year.
    """
    def parse_int_string(string: tp.Optional[str]) -> tp.Optional[int]:
        if string is None:
            return None

        try:
            return int(string)
        except ValueError:
            return None

    def get_or_create_stage_for_year(year: int) -> int:
        stages = case_study.stages
        num_stages = len(stages)

        for stage_index in range(num_stages):
            stage_year = parse_int_string(stages[stage_index].name)

            if stage_year is None:
                continue
            if stage_year == year:
                return stage_index
            if stage_year > year:
                continue
            if stage_year < year:
                case_study.insert_empty_stage(stage_index)
                case_study.name_stage(stage_index, str(year))
                return stage_index

        case_study.insert_empty_stage(num_stages)
        case_study.name_stage(num_stages, str(year))
        return num_stages

    repo_path = pygit2.discover_repository(kwargs['git_path'])
    repo = pygit2.Repository(repo_path)
    last_commit = repo[repo.head.target]
    revs_year_sep = kwargs['revs_year_sep']

    commits: tp.DefaultDict[int, tp.List[str]] = defaultdict(
        list)  # maps year -> list of commits
    for commit in repo.walk(last_commit.id, pygit2.GIT_SORT_TIME):
        commit_date = datetime.utcfromtimestamp(commit.commit_time)
        commits[commit_date.year].append(str(commit.id))

    new_rev_items = []  # new revisions that get added to to case_study
    for year, commits_in_year in commits.items():
        samples = min(len(commits_in_year), kwargs['revs_per_year'])
        sample_commit_indices = sorted(
            random.sample(range(len(commits_in_year)), samples))

        for commit_index in sample_commit_indices:
            commit_hash = commits_in_year[commit_index]
            time_id = cmap.time_id(commit_hash)
            new_rev_items.append((commit_hash, time_id))

        if revs_year_sep:
            stage_index = get_or_create_stage_for_year(year)
        else:
            stage_index = kwargs['merge_stage']

        case_study.include_revisions(new_rev_items, stage_index, True)
        new_rev_items.clear()


@check_required_args(['distribution', 'merge_stage', 'num_rev'])
def extend_with_distrib_sampling(case_study: CaseStudy, cmap: CommitMap,
                                 **kwargs: tp.Any) -> None:
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
        sample_n(distribution_function, kwargs['num_rev'], revision_list),
        kwargs['merge_stage'])


def sample_n(distrib_func: tp.Callable[[int], np.ndarray], num_samples: int,
             list_to_sample: tp.List[tp.Tuple[str, int]]
             ) -> tp.List[tp.Tuple[str, int]]:
    """
    Return a list of n unique samples.
    If the list to sample is smaller than the number of samples the full list
    is returned.

    Args:
        distrib_func: Distribution function with
                        f(n) -> [] where len([]) == n probabilities
        num_samples: number of samples to choose
        list_to_sample: list to sample from

    Returns:
        list[] of sampled items
    """
    if num_samples >= len(list_to_sample):
        return list_to_sample

    probabilities = distrib_func(len(list_to_sample))
    probabilities /= probabilities.sum()

    sampled_idxs = np.random.choice(
        len(list_to_sample), num_samples, replace=False, p=probabilities)

    return [list_to_sample[idx] for idx in sampled_idxs]


@check_required_args(['plot_type', 'boundary_gradient'])
def extend_with_smooth_revs(case_study: CaseStudy, cmap: CommitMap,
                            **kwargs: tp.Any) -> None:
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

    # Remove revision that are already present in another stage.
    new_revisions = [
        rev for rev in new_revisions if not case_study.has_revision(rev)
    ]
    if new_revisions:
        print("Found new revisions: ", new_revisions)
        case_study.include_revisions([(rev, cmap.time_id(rev))
                                      for rev in new_revisions],
                                     kwargs['merge_stage'])
    else:
        print("No new revisions found that where not already "
              "present in the case study.")
