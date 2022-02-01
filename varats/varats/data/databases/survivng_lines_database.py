import typing as tp

import pandas as pd
from pygit2._pygit2 import GIT_SORT_TOPOLOGICAL

from varats.data.cache_helper import load_cached_df_or_none, cache_dataframe
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.project.project_util import get_local_project_git
from varats.utils.git_util import calc_surviving_lines, FullCommitHash


class SurvivingLinesDatabase(
    EvaluationDatabase,
    cache_id="survivng_lines_data",
    columns=["commit_hash", "lines"]
):

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Dict[str, tp.Any]
    ) -> pd.DataFrame:
        data_frame = load_cached_df_or_none(cls.CACHE_ID, project_name)
        if data_frame is None:
            project_repo = get_local_project_git(case_study.project_name)
            data_dicts: tp.List[tp.Dict[str, tp.Any]] = []
            revisions = [
                FullCommitHash.from_pygit_commit(commit)
                for commit in project_repo.
                walk(project_repo.head.target, GIT_SORT_TOPOLOGICAL)
            ]
            for revision in revisions:
                lines_per_commit = calc_surviving_lines(
                    project_repo, revision, revisions
                )

                def build_dataframe_row(hash: FullCommitHash,
                                        lines: int) -> tp.Dict[str, tp.Any]:
                    data_dict: tp.Dict[str, tp.Any] = {
                        'revision': revision.to_short_commit_hash().hash,
                        'time_id': commit_map.time_id(revision),
                        'commit_hash': hash.hash,
                        'lines': lines
                    }
                    return data_dict

                for entry in lines_per_commit.items():
                    data_dicts.append(build_dataframe_row(entry[0], entry[1]))
            data_frame = pd.DataFrame(data_dicts)
            cache_dataframe(cls.CACHE_ID, project_name, data_frame)
        return data_frame
