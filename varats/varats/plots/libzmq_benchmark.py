import typing as tp

import numpy as np
import pandas
import pandas as pd
from matplotlib import pyplot as plt

from varats.data.databases.hidden_configurability_database import aggregate_data_for_cs
from varats.experiments.base.run_workloads import (
    MPRBinAggregate,
    MultiWLAggregate,
    RunPatchedWorkloads,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class LibZQMBenchmarkPlot(Plot, plot_name="libzmq_benchmark"):
    """Benchmark plot for libzmq."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    def load_benchmark_data(self) -> pandas.DataFrame:
        zmq_cs = get_loaded_paper_config().get_case_studies("libzmq")[0]
        zmq_data = aggregate_data_for_cs(zmq_cs, None)

        # Filter for metric "throughput_mb"
        zmq_data = zmq_data[zmq_data['metric'] == 'throughput_mb']

        # We want to prepare the data in a dataframe with the columnsL
        # "hwm", "message_size", "throughput_mb"

        data_rows = []

        # First, add the baseline data
        base_data = zmq_data[zmq_data['config_opportunity'] == "__baseline__"]
        for _, row in base_data.iterrows():
            # Extract message size from binary-wl column, which is in the format "bench-inproc-thr-{message_size}"
            message_size = int(row['binary-wl'].split('-')[-1])
            data_rows.append({
                'hwm': 1000,  # Default HWM value
                'message_size': message_size,
                'throughput_mb': np.mean(row['value'])
            })

        # Now, add the data for different HWM values
        zmq_data = zmq_data[zmq_data['config_opportunity'] == "default_hwm"]
        for _, row in zmq_data.iterrows():
            message_size = int(row['binary-wl'].split('-')[-1])
            hwm_value = int(row['variation'])
            if hwm_value == 1000:
                continue # Skip the default HWM value, as it's already included in the baseline
            data_rows.append({
                'hwm': hwm_value,
                'message_size': message_size,
                'throughput_mb': np.mean(row['value'])
            })

        return pd.DataFrame.from_records(data_rows)

    def plot(self, view_mode: bool) -> None:
        benchmark_data = self.load_benchmark_data()

        # One plot per HWM value
        hwms = sorted(benchmark_data["hwm"].unique())

        # plt.boxplot(
        #    [
        #        mean_data[mean_data['hwm'] == hwm]['relative_throughput']
        #        for hwm in hwms
        #    ],
        #    labels=hwms
        # )

        base_throughput = benchmark_data[benchmark_data['hwm'] == 1000].set_index('message_size')['throughput_mb']

        plt.figure(figsize=(6.4, 4.8*0.75))

        for hwm in hwms:
            print(hwm)
            if hwm not in [100,200,500,1000,1024,1500]:
                continue
            message_data = benchmark_data[benchmark_data['hwm'] == hwm].sort_values(
                by='message_size'
            )
            if hwm == 1000:
                plt.scatter(
                    message_data['message_size'],
                    message_data['throughput_mb'],
                    label=f'{int(hwm)} (Default)',
                    marker='*',
                    zorder=10,
                    s=125
                )
                continue
            plt.scatter(
                message_data['message_size'],
                message_data['throughput_mb'],
                label=f'{int(hwm)}',
                zorder=1,
                s=125
            )

            # Print relative improvement compared to baseline
            for _, row in message_data.iterrows():
                message_size = row['message_size']
                throughput = row['throughput_mb']
                baseline_throughput = base_throughput.get(message_size, None)
                if baseline_throughput is not None:
                    relative_improvement = (throughput - baseline_throughput) / baseline_throughput * 100
                    print(f"Message Size: {message_size} B, HWM: {hwm}, Throughput: {throughput:.2f} MB/s, Baseline: {baseline_throughput:.2f} MB/s, Relative Improvement: {relative_improvement:.2f}%")

        plt.xlabel('Message size (B)')
        plt.ylabel('Throughput (MB/s)')
        plt.xscale('log', base=2)
        plt.yscale('log', base=10)
        plt.legend(title="Alternative value",alignment="left", fontsize=9)
        plt.xticks([2**i for i in range(10, 20)])


class LibZMQBenchmarkPlotGenerator(
    PlotGenerator, generator_name="libzmq-benchmark", options=[]
):
    """Benchmark plot generator for libzmq."""

    def generate(self) -> tp.List[Plot]:
        return [LibZQMBenchmarkPlot(self.plot_config, **self.plot_kwargs)]
