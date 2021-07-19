"""Test artefacts config tool."""
import typing as tp
import unittest
import unittest.mock as mock
from pathlib import Path

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.data.discover_reports import initialize_reports
from varats.paper_mgmt.artefacts import (
    Artefact,
    ArtefactType,
    TableArtefact,
    PlotArtefact,
)
from varats.paper_mgmt.paper_config import get_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import prepare_plots
from varats.plots.discover_plots import initialize_plots
from varats.table.table import Table
from varats.table.tables import prepare_tables
from varats.tables.discover_tables import initialize_tables
from varats.tools.driver_artefacts import _artefact_generate
from varats.utils.settings import vara_cfg


def _mock_plot(plot: Plot):
    (
        Path(plot.plot_kwargs["plot_dir"]) /
        plot.plot_file_name(filetype=plot.plot_kwargs['file_type'])
    ).touch()


def _mock_table(table: Table):
    (Path(table.table_kwargs["table_dir"]) / table.table_file_name()).touch()


class TestDriverArtefacts(unittest.TestCase):
    """Tests for the driver_artefacts module."""

    @classmethod
    def setUp(cls):
        """Setup artefacts file from yaml doc."""
        initialize_reports()
        initialize_tables()
        initialize_plots()

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    @mock.patch('varats.table.tables.build_table', side_effect=_mock_table)
    @mock.patch('varats.plot.plots.build_plot', side_effect=_mock_plot)
    # pylint: disable=unused-argument
    def test_artefacts_generate(self, build_plots, build_tables):
        """Test whether `vara-art generate` generates all expected files."""

        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        artefacts = get_paper_config().get_all_artefacts()
        output_path = Path("artefacts/test_artefacts_driver")
        output_path.mkdir(parents=True)

        # vara-art generate
        _artefact_generate({})
        # check that overview files are present
        self.assertTrue((output_path / "index.html").exists())
        self.assertTrue((output_path / "plot_matrix.html").exists())
        # check that artefact files are present
        for artefact in artefacts:
            self.__check_artefact_files_present(artefact)

    def __check_artefact_files_present(self, artefact: Artefact):
        artefact_file_names: tp.List[str] = []
        if artefact.artefact_type == ArtefactType.PLOT:
            artefact = tp.cast(PlotArtefact, artefact)
            plots = prepare_plots(
                plot_type=artefact.plot_type,
                result_output=artefact.output_path,
                file_format=artefact.file_format,
                **artefact.plot_kwargs
            )
            artefact_file_names = [
                plot.plot_file_name(artefact.file_format) for plot in plots
            ]
        elif artefact.artefact_type == ArtefactType.TABLE:
            artefact = tp.cast(TableArtefact, artefact)
            tables = prepare_tables(
                table_type=artefact.table_type,
                result_output=artefact.output_path,
                file_format=artefact.file_format,
                **artefact.table_kwargs
            )
            artefact_file_names = [table.table_file_name() for table in tables]
        for file in artefact_file_names:
            self.assertTrue((artefact.output_path / file).exists())
