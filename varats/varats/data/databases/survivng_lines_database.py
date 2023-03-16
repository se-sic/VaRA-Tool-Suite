import typing as tp

import pandas as pd
from pygit2._pygit2 import GIT_SORT_TOPOLOGICAL

from varats.data.cache_helper import load_cached_df_or_none, cache_dataframe
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.project.project_util import get_local_project_git
from varats.utils.git_util import (
    calc_surviving_lines,
    FullCommitHash,
    ShortCommitHash,
)


class SurvivingLinesDatabase(
    EvaluationDatabase,
    cache_id="survivng_lines_data",
    column_types={
        "commit_hash": 'str',
        "lines": 'int32'
    }
):

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Dict[str, tp.Any]
    ) -> pd.DataFrame:
        data_frame = load_cached_df_or_none(
            cls.CACHE_ID, project_name, cls.COLUMN_TYPES
        )
        project_repo = get_local_project_git(case_study.project_name)
        revisions = case_study.revisions if case_study else [
            FullCommitHash.from_pygit_commit(commit) for commit in
            project_repo.walk(project_repo.head.target, GIT_SORT_TOPOLOGICAL)
        ]
        data_dicts: tp.List[tp.Dict[str, tp.Any]] = []
        cached_revisions = data_frame.groupby("revision").groups.keys(
        ) if data_frame is not None else set()
        revisions_to_compute = set(
            map(lambda r: r.hash, revisions)
        ) - cached_revisions

        for revision in revisions_to_compute:
            lines_per_commit = calc_surviving_lines(
                case_study.project_name, ShortCommitHash(revision)
            )

            def build_dataframe_row(chash: FullCommitHash,
                                    lines: int) -> tp.Dict[str, tp.Any]:
                data_dict: tp.Dict[str, tp.Any] = {
                    'revision': revision,
                    'time_id': commit_map.time_id(FullCommitHash(revision)),
                    'commit_hash': chash.hash,
                    'lines': lines
                }
                return data_dict

            for entry in lines_per_commit.items():
                data_dicts.append(build_dataframe_row(entry[0], entry[1]))
        if data_frame is None:
            data_frame = pd.DataFrame(data_dicts)
        else:
            data_frame = data_frame.append(pd.DataFrame(data_dicts))
        cache_dataframe(cls.CACHE_ID, project_name, data_frame)
        return data_frame
