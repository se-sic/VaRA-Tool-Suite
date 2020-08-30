"""A case study is used to pin down the exact set of revisions that should be
analysed for a project."""
import random
import typing as tp
from collections import defaultdict
from datetime import datetime
from enum import Enum
from itertools import groupby
from pathlib import Path

import numpy as np
import pygit2
from benchbuild import Project
from scipy.stats import halfnorm

from varats.data.provider.release.release_provider import (
    ReleaseProvider,
    ReleaseType,
)
from varats.data.report import FileStatusExtension, MetaReport
from varats.data.reports.commit_report import CommitMap
from varats.data.revisions import (
    get_failed_revisions,
    get_processed_revisions,
    get_tagged_revision,
    get_tagged_revisions,
    filter_blocked_revisions,
    is_revision_blocked,
)
from varats.data.version_header import VersionHeader
from varats.plots.plot_utils import check_required_args
from varats.plots.plots import PlotRegistry
from varats.utils.project_util import get_project_cls_by_name
from varats.utils.yaml_util import load_yaml, store_as_yaml


class ExtenderStrategy(Enum):
    """Enum for all currently supported extender strategies."""

    mixed = -1
    simple_add = 1
    distrib_add = 2
    smooth_plot = 3
    per_year_add = 4
    release_add = 5


class SamplingMethod(Enum):
    """Enum for all currently supported sampling methods."""

    uniform = 1
    half_norm = 2

    def gen_distribution_function(self) -> tp.Callable[[int], np.ndarray]:
        """
        Generate a distribution function for the specified sampling method.

        Returns:
            a callable that allows the caller to draw ``n`` numbers
            according to the selected distribution
        """
        if self == SamplingMethod.uniform:

            def uniform(num_samples: int) -> np.ndarray:
                return tp.cast(
                    tp.List[float], np.random.uniform(0, 1.0, num_samples)
                )

            return uniform
        if self == SamplingMethod.half_norm:

            def halfnormal(num_samples: int) -> np.ndarray:
                return tp.cast(
                    tp.List[float], halfnorm.rvs(scale=1, size=num_samples)
                )

            return halfnormal

        raise Exception('Unsupported SamplingMethod')


class HashIDTuple():
    """Combining a commit hash with a unique and ordered id, starting with 0 for
    the first commit in the repository."""

    def __init__(self, commit_hash: str, commit_id: int) -> None:
        self.__commit_hash = commit_hash
        self.__commit_id = commit_id

    @property
    def commit_hash(self) -> str:
        """A commit hash from the git repository."""
        return self.__commit_hash

    @property
    def commit_id(self) -> int:
        """The order ID of the commit hash."""
        return self.__commit_id

    def get_dict(self) -> tp.Dict[str, tp.Union[str, int]]:
        """Get a dict representation of this commit and id."""
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
    A stage in a case-study, i.e., a collection of revisions.

    Stages are used to separate revisions into groups.
    """

    def __init__(
        self,
        name: tp.Optional[str] = None,
        extender_strategy: tp.Optional[ExtenderStrategy] = None,
        sampling_method: tp.Optional[SamplingMethod] = None,
        release_type: tp.Optional[ReleaseType] = None,
        revisions: tp.Optional[tp.List[HashIDTuple]] = None
    ) -> None:
        self.__name: tp.Optional[str] = name
        self.__extender_strategy: tp.Optional[ExtenderStrategy] = \
            extender_strategy
        self.__sampling_method: tp.Optional[SamplingMethod] = sampling_method
        self.__release_type: tp.Optional[ReleaseType] = release_type
        self.__revisions: tp.List[HashIDTuple
                                 ] = revisions if revisions is not None else []

    @property
    def revisions(self) -> tp.List[str]:
        """Project revisions that are part of this case study."""
        return [x.commit_hash for x in self.__revisions]

    @property
    def name(self) -> tp.Optional[str]:
        """Name of the stage."""
        return self.__name

    @name.setter
    def name(self, name: str) -> None:
        """Setter for the name of the stage."""
        self.__name = name

    @property
    def extender_strategy(self) -> tp.Optional[ExtenderStrategy]:
        """The extender strategy used to create this stage."""
        return self.__extender_strategy

    @extender_strategy.setter
    def extender_strategy(self, extender_strategy: ExtenderStrategy) -> None:
        """Setter for the extender strategy of the stage."""
        self.__extender_strategy = extender_strategy

    @property
    def sampling_method(self) -> tp.Optional[SamplingMethod]:
        """The sampling method used for this stage."""
        return self.__sampling_method

    @sampling_method.setter
    def sampling_method(self, sampling_method: SamplingMethod) -> None:
        """Setter for the sampling method of the stage."""
        self.__sampling_method = sampling_method

    @property
    def release_type(self) -> tp.Optional[ReleaseType]:
        """The sampling method used for this stage."""
        return self.__release_type

    @release_type.setter
    def release_type(self, release_type: ReleaseType) -> None:
        """Setter for the sampling method of the stage."""
        self.__release_type = release_type

    def has_revision(self, revision: str) -> bool:
        """
        Check if a revision is part of this case study.

        Args:
            revision: project revision to check

        Returns:
            ``True``, in case the revision is part of the case study,
            ``False`` otherwise.
        """
        for cs_revision in self.__revisions:
            if cs_revision.commit_hash.startswith(revision):
                return True

        return False

    def add_revision(self, revision: str, commit_id: int) -> None:
        """
        Add a new revision to this stage.

        Args:
            revision: to add
            commit_id: unique ID for ordering of commits
        """
        if not self.has_revision(revision):
            self.__revisions.append(HashIDTuple(revision, commit_id))

    def sort(self, reverse: bool = True) -> None:
        """Sort the revisions of the case study by commit ID inplace."""
        self.__revisions.sort(key=lambda x: x.commit_id, reverse=reverse)

    def get_dict(
        self
    ) -> tp.Dict[str, tp.Union[str, tp.List[tp.Dict[str, tp.Union[str, int]]]]]:
        """Get a dict representation of this stage."""
        stage_dict: tp.Dict[str,
                            tp.Union[str,
                                     tp.List[tp.Dict[str,
                                                     tp.Union[str,
                                                              int]]]]] = dict()
        if self.name is not None:
            stage_dict['name'] = self.name
        if self.extender_strategy is not None:
            stage_dict['extender_strategy'] = self.extender_strategy.name
        if self.sampling_method is not None:
            stage_dict['sampling_method'] = self.sampling_method.name
        if self.release_type is not None:
            stage_dict['release_type'] = self.release_type.name
        revision_list = [revision.get_dict() for revision in self.__revisions]
        stage_dict['revisions'] = revision_list
        return stage_dict


class CaseStudy():
    """
    A case study persists a set of revisions of a project to allow easy
    reevaluation.

    Stored values:
     - name of the related benchbuild.project
     - a set of revisions
    """

    def __init__(
        self,
        project_name: str,
        version: int,
        stages: tp.Optional[tp.List[CSStage]] = None
    ) -> None:
        self.__project_name = project_name
        self.__version = version
        self.__stages = stages if stages is not None else []

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

        The version differentiates case studies of the same project.
        """
        return self.__version

    @property
    def revisions(self) -> tp.List[str]:
        """Project revisions that are part of this case study."""
        return list(
            dict.fromkeys([
                x for stage in self.__stages for x in stage.revisions
            ])
        )

    @property
    def stages(self) -> tp.List[CSStage]:
        """Get a list with all stages."""
        # Return new list to forbid modification of the case-study
        return list(self.__stages)

    @property
    def num_stages(self) -> int:
        """Get nummer of stages."""
        return len(self.__stages)

    def get_stage_by_name(self, stage_name: str) -> tp.Optional[CSStage]:
        """
        Get a stage by its name. Since multiple stages can have the same name,
        the first matching stage is returned.

        Args:
            stage_name: name of the stage to lookup

        Returns:
            the stage, corresponding with the 'stage_name', or ``None``
        """
        for stage in self.__stages:
            if stage.name == stage_name:
                return stage

        return None

    def get_stage_index_by_name(self, stage_name: str) -> tp.Optional[int]:
        """
        Get a stage's index by its name. Since multiple stages can have the same
        name, the first matching stage is returned.

        Args:
            stage_name: name of the stage to lookup

        Returns:
            the stage index, corresponding with the 'stage_name', or ``None``
        """
        for i in range(len(self.__stages)):
            if self.__stages[i].name == stage_name:
                return i

        return None

    def has_revision(self, revision: str) -> bool:
        """
        Check if a revision is part of this case study.

        Returns:
            ``True``, if the revision was found in one of the stages,
            ``False`` otherwise
        """
        for stage in self.__stages:
            if stage.has_revision(revision):
                return True

        return False

    def has_revision_in_stage(self, revision: str, num_stage: int) -> bool:
        """
        Checks if a revision is in a specific stage.

        Returns:
            ``True``, if the revision was found in the specified stage,
            ``False`` otherwise
        """
        if self.num_stages <= num_stage:
            return False
        return self.__stages[num_stage].has_revision(revision)

    def shift_stage(self, from_index: int, offset: int) -> None:
        """
        Shift a stage in the case-studie's stage list by an offset. Beware that
        shifts to the left (offset<0) will destroy stages.

        Args:
            from_index: index of the first stage to shift
            offset: amount to stages should be shifted
        """
        # keep parens for clarification
        if not (0 <= from_index < len(self.__stages)):  # pylint: disable=C0325
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
        Insert a new stage at the given index, shifting the list elements to the
        right. The newly created stage is returned.

        Args:
            pos: index position to insert an empty stage
        """
        new_stage = CSStage()
        self.__stages.insert(pos, new_stage)
        return new_stage

    def include_revision(
        self,
        revision: str,
        commit_id: int,
        stage_num: int = 0,
        sort_revs: bool = True
    ) -> None:
        """
        Add a revision to this case study.

        Args:
            revision: to add
            commit_id: unique ID for ordering of commits
            stage_num: index number of the stage to add the revision to
            sort_revs: if True, the modified stage will be sorted afterwards
        """
        # Create missing stages
        while self.num_stages <= stage_num:
            self.__stages.append(CSStage())

        stage = self.__stages[stage_num]

        if not stage.has_revision(revision):
            stage.add_revision(revision, commit_id)
            if sort_revs:
                stage.sort()

    def include_revisions(
        self,
        revisions: tp.List[tp.Tuple[str, int]],
        stage_num: int = 0,
        sort_revs: bool = True,
        extender_strategy: tp.Optional[ExtenderStrategy] = None,
        sampling_method: tp.Optional[SamplingMethod] = None,
        release_type: tp.Optional[ReleaseType] = None
    ) -> None:
        """
        Add multiple revisions to this case study.

        Args:
            revisions: List of tuples with (commit_hash, id) to be inserted
            stage_num: The stage to insert the revisions
            sort_revs: True if the stage should be kept sorted
            extender_strategy: The extender strategy used to acquire the
                               revisions
            sampling_method: The sampling method used to acquire the revisions
        """
        for revision in revisions:
            self.include_revision(revision[0], revision[1], stage_num, False)

        if len(self.__stages) <= stage_num:
            for idx in range(len(self.__stages), stage_num + 1):
                self.insert_empty_stage(idx)

        stage = self.__stages[stage_num]

        if sort_revs and self.num_stages > 0:
            self.__stages[stage_num].sort()

        if extender_strategy is not None:
            # if different strategies are used on the same stage,
            # the result is 'mixed'.
            # Also if sampled multiple times with a distribution.
            if (
                stage.extender_strategy is not None and (
                    stage.extender_strategy is not extender_strategy or
                    stage.extender_strategy is ExtenderStrategy.distrib_add
                )
            ):
                stage.extender_strategy = ExtenderStrategy.mixed
                stage.sampling_method = None
            else:
                stage.extender_strategy = extender_strategy
                if sampling_method is not None:
                    stage.sampling_method = sampling_method
                if release_type is not None:
                    stage.release_type = release_type.merge(stage.release_type)

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
        Generate a case study specific revision filter that only allows revision
        that are part of the case study.

        Returns:
            a callable filter function
        """

        def revision_filter(revision: str) -> bool:
            return self.has_revision(revision)

        return revision_filter

    def processed_revisions(self, result_file_type: MetaReport) -> tp.List[str]:
        """
        Computes all revisions of this case study that have been processed.

        Returns:
            a list of processed revisions
        """
        total_processed_revisions = set(
            get_processed_revisions(self.project_name, result_file_type)
        )

        return [
            rev for rev in self.revisions
            if rev[:10] in total_processed_revisions
        ]

    def failed_revisions(self, result_file_type: MetaReport) -> tp.List[str]:
        """
        Computes all revisions of this case study that have failed.

        Returns:
            a list of failed revisions
        """
        total_failed_revisions = set(
            get_failed_revisions(self.project_name, result_file_type)
        )

        return [
            rev for rev in self.revisions if rev[:10] in total_failed_revisions
        ]

    def get_revisions_status(
        self,
        result_file_type: MetaReport,
        stage_num: int = -1,
        tag_blocked: bool = True
    ) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
        """
        Computes the file status for all revisions in this case study.

        Returns:
            a list of (revision, status) tuples
        """
        project_cls = get_project_cls_by_name(self.project_name)
        tagged_revisions = get_tagged_revisions(
            project_cls, result_file_type, tag_blocked
        )

        def filtered_tagged_revs(
            rev_provider: tp.Iterable[str]
        ) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
            filtered_revisions = []
            for rev in rev_provider:
                found = False
                short_rev = rev[:10]
                for tagged_rev in tagged_revisions:
                    if short_rev == tagged_rev[0][:10]:
                        filtered_revisions.append(tagged_rev)
                        found = True
                        break
                if not found:
                    if tag_blocked and is_revision_blocked(
                        short_rev, project_cls
                    ):
                        filtered_revisions.append(
                            (short_rev, FileStatusExtension.Blocked)
                        )
                    else:
                        filtered_revisions.append(
                            (short_rev, FileStatusExtension.Missing)
                        )
            return filtered_revisions

        if stage_num == -1:
            return filtered_tagged_revs(self.revisions)

        if stage_num < self.num_stages:
            stage = self.__stages[stage_num]
            return filtered_tagged_revs(stage.revisions)

        return []

    def get_revision_status(
        self,
        revision: str,
        result_file_type: MetaReport,
    ) -> FileStatusExtension:
        """
        Computes the file status for the given revision in this case study.

        Returns:
            a list of (revision, status) tuples
        """
        if not self.has_revision(revision):
            raise ValueError(f"Case study has no revision {revision}")

        return get_tagged_revision(
            revision, self.project_name, result_file_type
        )

    def get_dict(
        self
    ) -> tp.Dict[str, tp.Union[str, int, tp.List[tp.Dict[str, tp.Union[
        str, tp.List[tp.Dict[str, tp.Union[str, int]]]]]]]]:
        """Get a dict representation of this case study."""
        return dict(
            project_name=self.project_name,
            version=self.version,
            stages=[stage.get_dict() for stage in self.stages]
        )


def load_case_study_from_file(file_path: Path) -> CaseStudy:
    """
    Load a case study from a file.

    Args:
        file_path: path to the case study file
    """
    documents = load_yaml(file_path)
    version_header = VersionHeader(next(documents))
    version_header.raise_if_not_type("CaseStudy")
    version_header.raise_if_version_is_less_than(1)

    raw_case_study = next(documents)
    stages: tp.List[CSStage] = []
    for raw_stage in raw_case_study['stages']:
        hash_id_tuples: tp.List[HashIDTuple] = []
        for raw_hash_id_tuple in raw_stage['revisions']:
            hash_id_tuples.append(
                HashIDTuple(
                    raw_hash_id_tuple['commit_hash'],
                    raw_hash_id_tuple['commit_id']
                )
            )
        extender_strategy = raw_stage.get('extender_strategy') or None
        sampling_method = raw_stage.get('sampling_method') or None
        release_type = raw_stage.get('release_type') or None
        stages.append(
            CSStage(
                raw_stage.get('name') or None,
                ExtenderStrategy[extender_strategy]
                if extender_strategy is not None else None,
                SamplingMethod[sampling_method]
                if sampling_method is not None else None,
                ReleaseType[release_type] if release_type is not None else None,
                hash_id_tuples
            )
        )

    return CaseStudy(
        raw_case_study['project_name'], raw_case_study['version'], stages
    )


def store_case_study(case_study: CaseStudy, case_study_location: Path) -> None:
    """
    Store case study to file in the specified paper_config.

    Args:
        case_study: the case study to store
        case_study_location: can be either a path to a paper_config
                             or a direct path to a `.case_study` file
    """
    if case_study_location.suffix != '.case_study':
        file_name = "{project_name}_{version}.case_study".format(
            project_name=case_study.project_name, version=case_study.version
        )
        case_study_location /= file_name

    __store_case_study_to_file(case_study, case_study_location)


def __store_case_study_to_file(case_study: CaseStudy, file_path: Path) -> None:
    """Store case study to file."""
    store_as_yaml(
        file_path,
        [VersionHeader.from_version_number('CaseStudy', 1), case_study]
    )


def get_newest_result_files_for_case_study(
    case_study: CaseStudy, result_dir: Path, report_type: MetaReport
) -> tp.List[Path]:
    """
    Return all result files of a specific type that belong to a given case
    study. For revision with multiple files, the newest file will be selected.

    Returns:
        list of result file paths
    """
    files_to_store: tp.Dict[str, Path] = dict()

    result_dir /= case_study.project_name
    if not result_dir.exists():
        return []

    for opt_res_file in result_dir.iterdir():
        if report_type.is_correct_report_type(opt_res_file.name):
            commit_hash = report_type.get_commit_hash_from_result_file(
                opt_res_file.name
            )
            if case_study.has_revision(commit_hash):
                current_file = files_to_store.get(commit_hash, None)
                if current_file is None:
                    files_to_store[commit_hash] = opt_res_file
                else:
                    if (
                        current_file.stat().st_mtime <
                        opt_res_file.stat().st_mtime
                    ):
                        files_to_store[commit_hash] = opt_res_file

    return list(files_to_store.values())


def get_case_study_file_name_filter(
    case_study: tp.Optional[CaseStudy]
) -> tp.Callable[[str], bool]:
    """
    Generate a case study specific file-name filter function that allows the
    user to check if a file name is related to this case study.

    Returns:
        a filter function that returns ``True`` in cases where a revision of
        file belongs to this case study
    """

    def cs_filter(file_name: str) -> bool:
        """
        Filter files that are not in the case study.

        Returns:
            ``True`` if a case_study is set and the commit_hash of the file
            is not part of this case_study, otherwise, ``False``.
        """
        if case_study is None:
            return False

        commit_hash = MetaReport.get_commit_hash_from_result_file(file_name)
        return not case_study.has_revision(commit_hash)

    return cs_filter


def get_unique_cs_name(case_studies: tp.List[CaseStudy]) -> tp.List[str]:
    """
    Create a list of unique names for the given case studies.

    If a case studie's project ocurrs only in one case study in the list, choose
    the project name as the name, otherwise, add the case studie's version to
    the name.

    Args:
        case_studies: the list of case studies to generate names for

    Returns:
        a list of unique names for the given case studies in the same order

    Test:
    >>> get_unique_cs_name([CaseStudy("xz", 1), CaseStudy("gzip", 1)])
    ['xz', 'gzip']

    >>> get_unique_cs_name([CaseStudy("xz", 1), CaseStudy("xz", 2)])
    ['xz_1', 'xz_2']

    Test:
    >>> get_unique_cs_name([CaseStudy("xz", 1), CaseStudy("gzip", 1), \
        CaseStudy("xz", 2)])
    ['xz_1', 'gzip', 'xz_2']
    """
    sorted_cs = sorted(case_studies, key=lambda cs: cs.project_name)
    cs_names = dict(
        (k, list(v)) for k, v in groupby(sorted_cs, lambda cs: cs.project_name)
    )

    return [
        cs.project_name if len(cs_names[cs.project_name]) == 1 else
        f"{cs.project_name}_{cs.version}" for cs in case_studies
    ]


###############################################################################
# Case-study generation
###############################################################################


@check_required_args(['extra_revs', 'git_path'])
def generate_case_study(
    sampling_method: SamplingMethod, cmap: CommitMap, case_study_version: int,
    project_name: str, **kwargs: tp.Any
) -> CaseStudy:
    """
    Generate a case study for a given project.

    This function will draw `num_samples` revisions from the history of the
    given project and persists the selected set into a case study for
    evaluation.

    Args:
        sampling_method: to use for revision sampling
        cmap: commit map to map revisions to unique IDs
        case_study_version: version to set for the case study
        project_name: name of the project so sample from
        kwargs: additional args that should be passed on to the strategy

    Returns:
        a new case study
    """
    case_study = CaseStudy(project_name, case_study_version)

    if kwargs['revs_per_year'] > 0:
        extend_with_revs_per_year(case_study, cmap, **kwargs)

    if (
        sampling_method is SamplingMethod.half_norm or
        sampling_method is SamplingMethod.uniform
    ):
        extend_with_distrib_sampling(case_study, cmap, **kwargs)

    if kwargs['extra_revs']:
        extend_with_extra_revs(case_study, cmap, **kwargs)

    return case_study


###############################################################################
# Case-study extender
###############################################################################


def extend_case_study(
    case_study: CaseStudy, cmap: CommitMap, ext_strategy: ExtenderStrategy,
    **kwargs: tp.Any
) -> None:
    """
    Extend a case study inplace with new revisions according to the specified
    extender strategy.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        ext_strategy: determines how the case study should be extended
    """

    if ext_strategy is ExtenderStrategy.simple_add:
        extend_with_extra_revs(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.distrib_add:
        extend_with_distrib_sampling(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.smooth_plot:
        extend_with_smooth_revs(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.per_year_add:
        extend_with_revs_per_year(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.release_add:
        extend_with_release_revs(case_study, cmap, **kwargs)


@check_required_args(['extra_revs', 'merge_stage'])
def extend_with_extra_revs(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case_study with extra revisions, specified by the caller with
    kwargs['extra_revs'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    extra_revs = kwargs['extra_revs']
    merge_stage = kwargs['merge_stage']

    new_rev_items = [
        rev_item for rev_item in cmap.mapping_items()
        if any(map(rev_item[0].startswith, extra_revs))
    ]

    case_study.include_revisions(
        new_rev_items, merge_stage, True, ExtenderStrategy.simple_add
    )


@check_required_args([
    'git_path', 'revs_per_year', 'merge_stage', 'revs_year_sep'
])
def extend_with_revs_per_year(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case_study with ``n`` revisions per year, specifed by the caller
    with kwargs['revs_per_year'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
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

    repo = pygit2.Repository(pygit2.discover_repository(kwargs['git_path']))
    last_commit = repo[repo.head.target]
    revs_year_sep = kwargs['revs_year_sep']

    commits: tp.DefaultDict[int, tp.List[str]] = defaultdict(
        list
    )  # maps year -> list of commits
    for commit in repo.walk(last_commit.id, pygit2.GIT_SORT_TIME):
        commit_date = datetime.utcfromtimestamp(commit.commit_time)
        commits[commit_date.year].append(str(commit.id))

    new_rev_items = []  # new revisions that get added to to case_study
    project_cls = get_project_cls_by_name(case_study.project_name)
    for year, commits_in_year in commits.items():
        samples = min(len(commits_in_year), kwargs['revs_per_year'])
        sample_commit_indices = sorted(
            random.sample(range(len(commits_in_year)), samples)
        )

        for commit_index in sample_commit_indices:
            commit_hash = commits_in_year[commit_index]
            if kwargs["ignore_blocked"] and is_revision_blocked(
                commit_hash, project_cls
            ):
                continue
            time_id = cmap.time_id(commit_hash)
            new_rev_items.append((commit_hash, time_id))

        if revs_year_sep:
            stage_index = get_or_create_stage_for_year(year)
        else:
            stage_index = kwargs['merge_stage']

        case_study.include_revisions(
            new_rev_items, stage_index, True, ExtenderStrategy.per_year_add
        )
        new_rev_items.clear()


@check_required_args(['distribution', 'merge_stage', 'num_rev'])
def extend_with_distrib_sampling(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case study by sampling 'num_rev' new revisions, according to
    distribution specified with kwargs['distribution'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    is_blocked: tp.Callable[[str, tp.Type[tp.Any]], bool] = lambda rev, _: False
    if kwargs["ignore_blocked"]:
        is_blocked = is_revision_blocked

    # Needs to be sorted so the propability distribution over the length
    # of the list is the same as the distribution over the commits age history
    project_cls = get_project_cls_by_name(case_study.project_name)
    revision_list = [
        rev_item
        for rev_item in sorted(list(cmap.mapping_items()), key=lambda x: x[1])
        if not case_study.
        has_revision_in_stage(rev_item[0], kwargs['merge_stage']) and
        not is_blocked(rev_item[0], project_cls)
    ]

    distribution_function = kwargs['distribution'].gen_distribution_function()

    case_study.include_revisions(
        sample_n(distribution_function, kwargs['num_rev'], revision_list),
        kwargs['merge_stage'],
        extender_strategy=ExtenderStrategy.distrib_add,
        sampling_method=kwargs['distribution']
    )


def sample_n(
    distrib_func: tp.Callable[[int], np.ndarray], num_samples: int,
    list_to_sample: tp.List[tp.Tuple[str, int]]
) -> tp.List[tp.Tuple[str, int]]:
    """
    Return a list of n unique samples. If the list to sample is smaller than the
    number of samples the full list is returned.

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
        len(list_to_sample), num_samples, replace=False, p=probabilities
    )

    return [list_to_sample[idx] for idx in sampled_idxs]


@check_required_args(['plot_type', 'boundary_gradient'])
def extend_with_smooth_revs(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case study with extra revisions that could smooth plot curves. This
    can remove steep gradients that result from missing certain revisions when
    sampling.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    plot_type = PlotRegistry.get_class_for_plot_type(kwargs['plot_type'])

    kwargs['plot_case_study'] = case_study
    kwargs['cmap'] = cmap
    plot = plot_type(**kwargs)
    # convert input to float %
    boundary_gradient = kwargs['boundary_gradient'] / float(100)
    print("Using boundary gradient: ", boundary_gradient)
    new_revisions = plot.calc_missing_revisions(boundary_gradient)

    if kwargs["ignore_blocked"]:
        new_revisions = set(
            filter_blocked_revisions(
                list(new_revisions),
                get_project_cls_by_name(case_study.project_name)
            )
        )

    # Remove revision that are already present in another stage.
    new_revisions = {
        rev for rev in new_revisions if not case_study.has_revision(rev)
    }
    if new_revisions:
        print("Found new revisions: ", new_revisions)
        case_study.include_revisions(
            [(rev, cmap.time_id(rev)) for rev in new_revisions],
            kwargs['merge_stage'],
            extender_strategy=ExtenderStrategy.smooth_plot
        )
    else:
        print(
            "No new revisions found that where not already "
            "present in the case study."
        )


@check_required_args(['project', 'release_type', 'merge_stage'])
def extend_with_release_revs(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case study with revisions marked as a release. This extender relies
    on the project to determine appropriate revisions.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    project_cls: tp.Type[Project] = get_project_cls_by_name(kwargs['project'])
    release_provider = ReleaseProvider.get_provider_for_project(project_cls)
    release_revisions: tp.List[str] = [
        revision for revision, release in
        release_provider.get_release_revisions(kwargs['release_type'])
    ]

    if kwargs["ignore_blocked"]:
        release_revisions = filter_blocked_revisions(
            release_revisions, project_cls
        )

    case_study.include_revisions([
        (rev, cmap.time_id(rev)) for rev in release_revisions
    ],
                                 kwargs['merge_stage'],
                                 extender_strategy=ExtenderStrategy.release_add,
                                 release_type=kwargs['release_type'])
