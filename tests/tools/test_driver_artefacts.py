"""Test artefacts config tool."""
import unittest
import unittest.mock as mock
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.data.discover_reports import initialize_reports
from varats.paper_mgmt.artefacts import Artefact
from varats.paper_mgmt.paper_config import get_paper_config, load_paper_config
from varats.plots.discover_plots import initialize_plots
from varats.table.table import Table
from varats.tables.discover_tables import initialize_tables
from varats.tools import driver_artefacts
from varats.utils.settings import vara_cfg


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
    # pylint: disable=unused-argument
    def test_artefacts_generate(self, build_tables):
        """Test whether `vara-art generate` generates all expected files."""

        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        load_paper_config()
        artefacts = get_paper_config().get_all_artefacts()
        base_output_dir = Artefact.base_output_dir()

        # vara-art generate
        runner = CliRunner()
        result = runner.invoke(driver_artefacts.main, ["generate"])
        self.assertEqual(0, result.exit_code, result.exception)

        # check that overview files are present
        self.assertTrue((base_output_dir / "index.html").exists())
        self.assertTrue((base_output_dir / "plot_matrix.html").exists())
        # check that artefact files are present
        for artefact in artefacts:
            self.__check_artefact_files_present(artefact)

    def __check_artefact_files_present(self, artefact: Artefact):
        for file_info in artefact.get_artefact_file_infos():
            self.assertTrue((artefact.output_dir / file_info.file_name).exists()
                           )

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    def test_artefacts_list(self):
        """Test whether `vara-art list` produces expected output."""

        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        load_paper_config()

        # vara-art generate
        runner = CliRunner()
        result = runner.invoke(driver_artefacts.main, ["list"])
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertEqual(
            "Paper Config Overview [plot]\nCorrelation Table [table]\n",
            result.stdout
        )

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    def test_artefacts_show(self):
        """Test whether `vara-art show` produces expected output."""

        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        load_paper_config()

        expected = r"""Artefact 'Paper Config Overview':
  artefact_type: plot
  artefact_type_version: 2
  dry_run: false
  file_type: png
  name: Paper Config Overview
  output_dir: .
  plot_config: {}
  plot_generator: pc-overview-plot
  report_type: EmptyReport
  view: false

"""

        # vara-art generate
        runner = CliRunner()
        result = runner.invoke(
            driver_artefacts.main, ["show", "Paper Config Overview"]
        )
        self.assertEqual(0, result.exit_code, result.exception)
        self.assertEqual(expected, result.stdout)
