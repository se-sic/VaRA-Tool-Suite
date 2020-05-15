import typing as tp
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from varats.data.databases.blame_diff_metrics_database import (
    BlameDiffMetricsDatabase,
)
from varats.paper.paper_config import get_paper_config
from varats.tables.table import Table, TableFormat
from varats.tools.commit_map import create_lazy_commit_map_loader


class OverviewTable(Table):

    NAME = "overview"

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_studies = get_paper_config().get_all_case_studies()

        cs_data = [
            BlameDiffMetricsDatabase.get_data_for_project(
                case_study.project_name, [
                    "revision", "churn_total", "diff_ci_total",
                    "ci_degree_mean", "author_mean", "avg_time_mean",
                    "ci_degree_max", "author_max", "avg_time_max", "year"
                ],
                create_lazy_commit_map_loader(case_study.project_name)(),
                case_study
            ) for case_study in case_studies
        ]
        for data in cs_data:
            data.set_index('revision', inplace=True)
            data.drop(data[data.churn_total == 0].index, inplace=True)

        vars_1 = [
            "churn_total", "diff_ci_total", "ci_degree_mean", "author_mean",
            "avg_time_mean"
        ]

        corelations = [data[vars_1].corr(method="pearson") for data in cs_data]

        df = pd.concat(
            corelations,
            axis=1,
            keys=[case_study.project_name for case_study in case_studies]
        )

        if self.format in [
            TableFormat.latex, TableFormat.latex_booktabs, TableFormat.latex_raw
        ]:
            return df.to_latex(bold_rows=True, multicolumn_format="c")
        return tabulate(df, df.columns, self.format.value)

    def save(self, path: tp.Optional[Path] = None) -> None:
        filetype = self.format_filetypes.get(self.format, "txt")

        if path is None:
            table_dir = Path(self.table_kwargs["table_dir"])
        else:
            table_dir = path

        table = self.tabulate()
        with open(table_dir / f"{self.name}.{filetype}", "w") as outfile:
            outfile.write(table)
