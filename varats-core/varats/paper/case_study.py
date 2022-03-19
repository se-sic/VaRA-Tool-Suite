"""A case study is used to pin down the exact set of revisions that should be
analysed for a project."""

import typing as tp
from pathlib import Path

import benchbuild as bb

from varats.base.configuration import Configuration
from varats.base.sampling_method import (
    NormalSamplingMethod,
    SamplingMethodBase,
    SamplingMethod,
)
from varats.base.version_header import VersionHeader
from varats.mapping.configuration_map import (
    ConfigurationMap,
    create_configuration_map_from_yaml_doc,
)
from varats.project.project_util import get_project_cls_by_name
from varats.provider.release.release_provider import ReleaseType
from varats.utils.git_util import ShortCommitHash, FullCommitHash, CommitHash
from varats.utils.yaml_util import load_yaml, store_as_yaml

CSEntryMapTypes = tp.Union[str, int, tp.List[int]]


class CSEntry():
    """Combining a commit hash with a unique and ordered id, starting with 0 for
    the first commit in the repository."""

    def __init__(
        self,
        commit_hash: FullCommitHash,
        commit_id: int,
        config_ids: tp.Optional[tp.List[int]] = None
    ) -> None:
        self.__commit_hash = commit_hash
        self.__commit_id = commit_id

        if config_ids:
            self.__config_ids: tp.List[int] = config_ids
        else:
            # By default we add a list with the DummyConfig ID if no
            # configurations were provided.
            self.__config_ids = [ConfigurationMap.DUMMY_CONFIG_ID]

    @property
    def commit_hash(self) -> FullCommitHash:
        """A commit hash from the git repository."""
        return self.__commit_hash

    @property
    def commit_id(self) -> int:
        """The order ID of the commit hash."""
        return self.__commit_id

    @property
    def config_ids(self) -> tp.List[int]:
        """The order ID of the configuration."""
        return self.__config_ids

    def get_dict(self) -> tp.Dict[str, CSEntryMapTypes]:
        """Get a dict representation of this commit and id."""
        return dict(
            commit_hash=self.commit_hash.hash,
            commit_id=self.commit_id,
            config_ids=self.config_ids
        )

    def __str__(self) -> str:
        return f"({self.commit_id}: #{self.commit_hash.hash})"

    def __repr__(self) -> str:
        return f"({self.commit_id}: #{self.commit_hash.hash})"


class CSStage():
    """
    A stage in a case-study, i.e., a collection of revisions.

    Stages are used to separate revisions into groups.
    """

    def __init__(
        self,
        name: tp.Optional[str] = None,
        sampling_method: tp.Optional[SamplingMethod] = None,
        release_type: tp.Optional[ReleaseType] = None,
        revisions: tp.Optional[tp.List[CSEntry]] = None
    ) -> None:
        self.__name: tp.Optional[str] = name
        self.__sampling_method: tp.Optional[SamplingMethod] = sampling_method
        self.__release_type: tp.Optional[ReleaseType] = release_type
        self.__revisions: tp.List[CSEntry
                                 ] = revisions if revisions is not None else []

    @property
    def revisions(self) -> tp.List[FullCommitHash]:
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
    def sampling_method(self) -> tp.Optional[SamplingMethod]:
        """The sampling method used for this stage."""
        return self.__sampling_method

    @sampling_method.setter
    def sampling_method(self, sampling_method: NormalSamplingMethod) -> None:
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

    def has_revision(self, revision: CommitHash) -> bool:
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

    def add_revision(
        self,
        revision: FullCommitHash,
        commit_id: int,
        config_ids: tp.Optional[tp.List[int]] = None
    ) -> None:
        """
        Add a new revision to this stage.

        Args:
            revision: to add
            commit_id: unique ID for ordering of commits
            config_ids: list of configuration IDs
        """
        if not self.has_revision(revision):
            self.__revisions.append(CSEntry(revision, commit_id, config_ids))

    def get_config_ids_for_revision(self, revision: CommitHash) -> tp.List[int]:
        """
        Returns a list of all configuration IDs specified for this revision.

        Args:
            revision: i.e., a commit hash registed in this ``CSStage``

        Returns: list of config IDs
        """
        return list({
            config_id for entry in self.__revisions
            if entry.commit_hash.startswith(revision)
            for config_id in entry.config_ids
        })

    def sort(self, reverse: bool = True) -> None:
        """Sort the revisions of the case study by commit ID inplace."""
        self.__revisions.sort(key=lambda x: x.commit_id, reverse=reverse)

    def get_dict(
        self
    ) -> tp.Dict[str, tp.Union[str, tp.List[tp.Dict[str, CSEntryMapTypes]]]]:
        """Get a dict representation of this stage."""
        stage_dict: tp.Dict[str,
                            tp.Union[str,
                                     tp.List[tp.Dict[str,
                                                     CSEntryMapTypes]]]] = {}
        if self.name is not None:
            stage_dict['name'] = self.name
        if self.sampling_method is not None:
            stage_dict['sampling_method'] = self.sampling_method.name()
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
    def project_cls(self) -> tp.Type[bb.Project]:
        """
        Look up the BenchBuild project for this case study.

        Returns:
            project class
        """
        return get_project_cls_by_name(self.project_name)

    @property
    def version(self) -> int:
        """
        Version ID for this case study.

        The version differentiates case studies of the same project.
        """
        return self.__version

    @property
    def revisions(self) -> tp.List[FullCommitHash]:
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
        for i, stage in enumerate(self.__stages):
            if stage.name == stage_name:
                return i

        return None

    def has_revision(self, revision: CommitHash) -> bool:
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

    def has_revision_in_stage(
        self, revision: ShortCommitHash, num_stage: int
    ) -> bool:
        """
        Checks if a revision is in a specific stage.

        Returns:
            ``True``, if the revision was found in the specified stage,
            ``False`` otherwise
        """
        if self.num_stages <= num_stage:
            return False
        return self.__stages[num_stage].has_revision(revision)

    def get_config_ids_for_revision(self, revision: CommitHash) -> tp.List[int]:
        """
        Returns a list of all configuration IDs specified for this revision.

        Args:
            revision: i.e., a commit hash registed in this case study

        Returns: list of config IDs
        """
        config_ids: tp.List[int] = []
        for stage in self.__stages:
            config_ids += stage.get_config_ids_for_revision(revision)

        if ConfigurationMap.DUMMY_CONFIG_ID in config_ids and len(
            config_ids
        ) > 1:
            config_ids.remove(ConfigurationMap.DUMMY_CONFIG_ID)

        return config_ids

    def get_config_ids_for_revision_in_stage(
        self, revision: CommitHash, num_stage: int
    ) -> tp.List[int]:
        """
        Returns a list of all configuration IDs specified for this revision.

        Args:
            revision: i.e., a commit hash registed in this case study
            num_stage: number of the stage to search in

        Returns: list of config IDs
        """
        if self.num_stages <= num_stage:
            return []

        return self.__stages[num_stage].get_config_ids_for_revision(revision)

    def shift_stage(self, from_index: int, offset: int) -> None:
        """
        Shift a stage in the case-studies' stage list by an offset. Beware that
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
        revision: FullCommitHash,
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
        revisions: tp.List[tp.Tuple[FullCommitHash, int]],
        stage_num: int = 0,
        sort_revs: bool = True
    ) -> None:
        """
        Add multiple revisions to this case study.

        Args:
            revisions: List of tuples with (commit_hash, id) to be inserted
            stage_num: The stage to insert the revisions
            sort_revs: True if the stage should be kept sorted
        """
        for revision in revisions:
            self.include_revision(revision[0], revision[1], stage_num, False)

        if len(self.__stages) <= stage_num:
            for idx in range(len(self.__stages), stage_num + 1):
                self.insert_empty_stage(idx)

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

    def get_revision_filter(self) -> tp.Callable[[CommitHash], bool]:
        """
        Generate a case study specific revision filter that only allows revision
        that are part of the case study.

        Returns:
            a callable filter function
        """

        def revision_filter(revision: CommitHash) -> bool:
            return self.has_revision(revision)

        return revision_filter

    def get_dict(
        self
    ) -> tp.Dict[str, tp.Union[str, int, tp.List[tp.Dict[str, tp.Union[
        str, tp.List[tp.Dict[str, CSEntryMapTypes]]]]]]]:
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
        hash_id_tuples: tp.List[CSEntry] = []
        for raw_hash_id_tuple in raw_stage['revisions']:
            if 'config_ids' in raw_hash_id_tuple:
                config_ids = [int(x) for x in raw_hash_id_tuple['config_ids']]
            else:
                config_ids = []

            hash_id_tuples.append(
                CSEntry(
                    FullCommitHash(raw_hash_id_tuple['commit_hash']),
                    raw_hash_id_tuple['commit_id'], config_ids
                )
            )

        sampling_method_name = raw_stage.get('sampling_method') or None

        if sampling_method_name:
            sampling_method: tp.Optional[SamplingMethod] = SamplingMethodBase[
                SamplingMethod].get_sampling_method_type(sampling_method_name)()
        else:
            sampling_method = None

        release_type = raw_stage.get('release_type') or None
        stages.append(
            CSStage(
                raw_stage.get('name') or None, sampling_method,
                ReleaseType[release_type] if release_type is not None else None,
                hash_id_tuples
            )
        )

    return CaseStudy(
        raw_case_study['project_name'], raw_case_study['version'], stages
    )


def load_configuration_map_from_case_study_file(
    file_path: Path, concrete_config_type: tp.Type[Configuration]
) -> ConfigurationMap:
    """
    Load a configuration map from a case-study file.

    Args:
        file_path: to the configuration map file
        concrete_config_type: type of the configuration objects that should be
                              created

    Returns: a new `ConfigurationMap` based on the parsed file
    """
    documents = load_yaml(file_path)
    version_header = VersionHeader(next(documents))
    version_header.raise_if_not_type("CaseStudy")
    version_header.raise_if_version_is_less_than(1)

    next(documents)  # Skip case study yaml-doc

    return create_configuration_map_from_yaml_doc(
        next(documents), concrete_config_type
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
        file_name = f"{case_study.project_name}_{case_study.version}.case_study"
        case_study_location /= file_name

    __store_case_study_to_file(case_study, case_study_location)


def __store_case_study_to_file(case_study: CaseStudy, file_path: Path) -> None:
    """Store case study to file."""
    store_as_yaml(
        file_path,
        [VersionHeader.from_version_number('CaseStudy', 1), case_study]
    )
