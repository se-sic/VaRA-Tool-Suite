"""
Module for comparing different cluster algorithms.

- cluster analysis
"""
import abc
import typing as tp
import warnings
from itertools import islice, cycle

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn import cluster, mixture
from sklearn.neighbors import kneighbors_graph
from sklearn.preprocessing import StandardScaler

from varats.data.databases.blame_diff_metrics_database import (
    BlameDiffMetricsDatabase,
)
from varats.mapping.commit_map import CommitMap
from varats.plot.plot import Plot, PlotDataEmpty
from varats.utils.git_util import FullCommitHash


def _create_cluster_objects(
    bandwidth: float, connectivity: tp.Any, params: tp.Dict[str, tp.Union[float,
                                                                          int]]
) -> tp.List[tp.Tuple[str, tp.Any]]:
    mean_shift = cluster.MeanShift(bandwidth=bandwidth, bin_seeding=True)
    two_means = cluster.MiniBatchKMeans(n_clusters=params['n_clusters'])
    ward = cluster.AgglomerativeClustering(
        n_clusters=params['n_clusters'],
        linkage='ward',
        connectivity=connectivity
    )
    spectral = cluster.SpectralClustering(
        n_clusters=params['n_clusters'],
        eigen_solver='arpack',
        affinity="nearest_neighbors"
    )
    dbscan = cluster.DBSCAN(eps=params['eps'])
    optics = cluster.OPTICS(
        min_samples=params['min_samples'],
        xi=params['xi'],
        min_cluster_size=params['min_cluster_size']
    )
    affinity_propagation = cluster.AffinityPropagation(
        damping=params['damping'], preference=params['preference']
    )
    average_linkage = cluster.AgglomerativeClustering(
        linkage="average",
        affinity="cityblock",
        n_clusters=params['n_clusters'],
        connectivity=connectivity
    )
    birch = cluster.Birch(n_clusters=params['n_clusters'])
    gmm = mixture.GaussianMixture(
        n_components=params['n_clusters'], covariance_type='full'
    )
    clustering_algorithms = [('MiniBatchKMeans', two_means),
                             ('AffinityPropagation', affinity_propagation),
                             ('MeanShift', mean_shift),
                             ('SpectralClustering', spectral), ('Ward', ward),
                             ('AgglomerativeClustering', average_linkage),
                             ('DBSCAN', dbscan), ('OPTICS', optics),
                             ('Birch', birch), ('GaussianMixture', gmm)]
    return clustering_algorithms


def _plot_cluster_comparison(
    datasets: tp.List[tp.Tuple[np.ndarray, str, str, tp.Dict[str, tp.Any]]]
) -> None:
    scale_factor = 1.5
    plt.figure(
        figsize=(10 * scale_factor + 1, len(datasets) * scale_factor + .5)
    )
    plt.subplots_adjust(
        left=.02,
        right=.98,
        bottom=.02,
        top=(len(datasets) * scale_factor) /
        (len(datasets) * scale_factor + .5),
        wspace=.02,
        hspace=.01
    )

    plot_num = 1

    default_base = {
        'quantile': .3,
        'eps': .3,
        'damping': .9,
        'preference': -200,
        'n_neighbors': 10,
        'n_clusters': 3,
        'min_samples': 20,
        'xi': 0.05,
        'min_cluster_size': 0.1
    }

    for i_dataset, (dataset, x_data, y_data,
                    algo_params) in enumerate(datasets):
        # update parameters with dataset-specific values
        params = default_base.copy()
        params.update(algo_params)

        dataset2 = dataset.copy()
        # normalize dataset for easier parameter selection
        dataset2 = StandardScaler().fit_transform(dataset2)

        # estimate bandwidth for mean shift
        bandwidth = cluster.estimate_bandwidth(
            dataset2, quantile=params['quantile']
        )

        # connectivity matrix for structured Ward
        connectivity = kneighbors_graph(
            dataset2, n_neighbors=params['n_neighbors'], include_self=False
        )
        # make connectivity symmetric
        connectivity = 0.5 * (connectivity + connectivity.VersionType)

        # Create cluster objects
        clustering_algorithms = _create_cluster_objects(
            bandwidth, connectivity, params
        )

        for i_algorithm, (name, algorithm) in enumerate(clustering_algorithms):
            # catch warnings related to kneighbors_graph
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="the number of connected components of the " +
                    "connectivity matrix is [0-9]{1,2}" +
                    " > 1. Completing it to avoid stopping the tree early.",
                    category=UserWarning
                )
                warnings.filterwarnings(
                    "ignore",
                    message="Graph is not fully connected, spectral embedding" +
                    " may not work as expected.",
                    category=UserWarning
                )
                algorithm.fit(dataset2)

            if hasattr(algorithm, 'labels_'):
                y_pred = algorithm.labels_.astype(np.int)
            else:
                y_pred = algorithm.predict(dataset2)

            plt.subplot(len(datasets), len(clustering_algorithms), plot_num)
            if i_dataset == 0:
                plt.title(name, size=10)
            if i_algorithm == 0:
                plt.ylabel(y_data, size=8, rotation=90)
            if i_dataset == len(datasets) - 1:
                plt.xlabel(x_data, size=8, rotation=90)

            colors = np.array(
                list(
                    islice(
                        cycle([
                            '#377eb8', '#ff7f00', '#4daf4a', '#f781bf',
                            '#a65628', '#984ea3', '#999999', '#e41a1c',
                            '#dede00'
                        ]), int(max(y_pred) + 1)
                    )
                )
            )
            # add black color for outliers (if any)
            colors = np.append(colors, ["#000000"])
            plt.scatter(
                dataset[:, 0], dataset[:, 1], s=10, color=colors[y_pred]
            )

            plt.xticks(())
            plt.yticks(())

            plot_num += 1


class BlameDiffClusterAnalysis(Plot):
    """Performs different cluster algorithms on blame-diff data."""

    NAME = "b_cluster_analysis"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        case_study = self.plot_kwargs.get('plot_case_study', None)
        project_name = self.plot_kwargs["project"]

        sns.set(style="ticks", color_codes=True)

        variables = [
            "churn", "num_interactions", "num_interacting_commits",
            "num_interacting_authors"
        ]
        df = BlameDiffMetricsDatabase.get_data_for_project(
            project_name, ["revision", *variables], commit_map, case_study
        )
        df.set_index('revision', inplace=True)
        df.drop(df[df.churn == 0].index, inplace=True)
        if df.empty:
            raise PlotDataEmpty

        _plot_cluster_comparison([
            (df[["churn", var]].to_numpy(), "churn", var, {})
            for var in variables
        ])

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError
