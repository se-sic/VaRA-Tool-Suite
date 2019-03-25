
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from varats.data.commit_report import CommitMap


def gen_fosd_graph():
    from varats.settings import CFG
    from varats.jupyterhelper.file import load_commit_report

    from pathlib import Path

    commit_map = CommitMap("/home/vulder/vara/c_map")

    reports = []
    result_dir = Path("/home/vulder/vara/fosd_results/")
    for file_path in result_dir.iterdir():
        if file_path.stem.startswith("gzip"):
            print("Loading file: ", file_path)
            reports.append(load_commit_report(file_path))

    def sorter(report):
        return commit_map.short_time_id(report.head_commit)

    reports = sorted(reports, key=sorter)

    # Sort with commit map
    commits = []
    df_interactions = []
    cf_interactions = []
    head_interactions = []

    for report in reports:
            commits.append(report.head_commit)
            df_interactions.append(report.number_of_df_interactions())
            cf_interactions.append(report.number_of_cf_interactions())
            hi = report.number_of_head_df_interactions()
            head_interactions.append(hi[0] + hi[1])

    df=pd.DataFrame({'x': commits, 'DFInteractions': df_interactions,
                     'CFInteractions': cf_interactions,
                     "HEAD Interactions": head_interactions})

    ax = plt.subplot()

    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
            # label.set_fontname('Arial')
            label.set_fontsize(14)

    plt.plot('x', 'DFInteractions', data=df, color='red')
    plt.plot('x', 'CFInteractions', data=df, color='blue')
    plt.xlabel("Revisions", **{'size': '14'})
    plt.ylabel("Interactions", **{'size': '14'})
    # plt.plot('x', 'HEAD Interactions', data=df, color='green')
    plt.show()


