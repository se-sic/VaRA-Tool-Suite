import typing as tp

import pandas
from matplotlib import pyplot as plt

from varats.experiments.base.run_workloads import RunWorkloads, MPRBinAggregate, MultiWLAggregate
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class LibZQMBenchmarkPlot(Plot, plot_name="libzmq_benchmark"):
    """
    Benchmark plot for libzmq.
    """

    def __extract_data(self, multi_wl_report: MultiWLAggregate, hwm: int) -> tp.List[tp.Dict[str, tp.Any]]:
        data_rows = []
        for workload in multi_wl_report.keys():
            for text_report in multi_wl_report[workload]:
                repetition = text_report.filename.filename.split("_")[-1].split('.')[0]
                new_row = {
                    "hwm": hwm,
                    "rep": repetition
                }
                with open(text_report.path, "r") as report_file:
                    for line in report_file:
                        if "message size" in line:
                            new_row["message_size"] = int(line.split(" ")[2].strip())
                        if "count" in line:
                            new_row["count"] = int(line.split(" ")[2].strip())
                        if "latency" in line:
                            new_row["latency"] = float(line.split(" ")[2].strip())
                        if "throughput" in line and "msg/s" in line:
                            new_row["throughput_msg"] = float(line.split(" ")[2].strip())
                        if "throughput" in line and "Mb/s" in line:
                            new_row["throughput_mb"] = float(line.split(" ")[2].strip())

                data_rows.append(new_row)

        return data_rows

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    def load_benchmark_data(self) -> pandas.DataFrame:
        libzmq_cs = get_loaded_paper_config().get_case_studies("libzmq")[0]

        # TODO: Consider multiple configurations?

        report_files = get_processed_revisions_files(
            libzmq_cs.project_name, RunWorkloads, MPRBinAggregate, get_case_study_file_name_filter(libzmq_cs)
        )

        if len(report_files) > 1:
            raise AssertionError("Found more than one report file.")
        if not report_files:
            print(
                f"Could not find benchmark data for {libzmq_cs.project_name}."
            )
            return pandas.DataFrame()

        report_data = MPRBinAggregate(report_files[0].full_path())

        data_rows = []

        for base_name in report_data.get_baseline_names():
            base_report = report_data.get_specific_baseline_report(base_name)

            data_rows.extend(self.__extract_data(base_report, 1000))

            for patch_name in report_data.get_patch_names():
                patch_report = report_data.get_specific_patched_report(base_name, patch_name)

                hwm = int(patch_name.split("_")[-1])
                data_rows.extend(self.__extract_data(patch_report, hwm))

        df = pandas.DataFrame(data_rows)
        df = df.groupby(["hwm", "message_size", "rep"], as_index=False).first()
        return df

    def plot(self, view_mode: bool) -> None:
        benchmark_data = self.load_benchmark_data()

        benchmark_data = benchmark_data[benchmark_data['message_size'] >= 2**15]

        mean_data = benchmark_data.groupby(['hwm', 'message_size'], as_index=False).agg(
            {
                'throughput_mb': 'mean',
                'throughput_msg': 'mean',
                'latency': 'mean',
                'rep': 'count',
            }
        )

        reference_df = mean_data[mean_data['hwm'] == 1000]
        reference_throughput = reference_df.set_index("message_size")['throughput_mb']

        mean_data['relative_throughput'] = mean_data.apply(
            lambda row: row['throughput_mb'] / reference_throughput[row['message_size']], axis=1
        )

        # One plot per HWM value
        hwms = sorted(benchmark_data["hwm"].unique())

        # plt.boxplot(
        #    [
        #        mean_data[mean_data['hwm'] == hwm]['relative_throughput']
        #        for hwm in hwms
        #    ],
        #    labels=hwms
        # )

        for hwm in hwms:
            message_data = mean_data[mean_data['hwm'] == hwm].sort_values(by='message_size')
            if hwm == 1000:
                plt.scatter(message_data['message_size'], message_data['throughput_mb'],
                            label=f'HWM: {int(hwm)} (Default)', marker='*')
                continue

            plt.scatter(message_data['message_size'], message_data['throughput_mb'], label=f'HWM: {int(hwm)}')

        plt.xlabel('Message size (B)')
        plt.ylabel('Relative throughput (Compared to HWM 1000)')
        plt.xscale('log', base=2)
        plt.legend()
        plt.xticks([2 ** i for i in range(15, 20)])


class LibZMQBenchmarkPlotGenerator(PlotGenerator, generator_name="libzmq-benchmark", options=[]):
    """
    Benchmark plot generator for libzmq.
    """

    def generate(self) -> tp.List[Plot]:
        return [LibZQMBenchmarkPlot(self.plot_config, **self.plot_kwargs)]
