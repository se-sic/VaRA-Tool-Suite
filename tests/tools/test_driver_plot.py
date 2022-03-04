"""Test artefacts config tool."""
import unittest
from pathlib import Path

from click.testing import CliRunner

from tests.test_utils import run_in_test_environment, UnitTestInputs
from varats.paper_mgmt.paper_config import get_paper_config, load_paper_config
from varats.plot.plots import PlotArtefact
from varats.tools import driver_plot
from varats.utils.settings import vara_cfg, save_config


class TestDriverPlot(unittest.TestCase):
    """Tests for the driver_plot module."""

    @run_in_test_environment(
        UnitTestInputs.PAPER_CONFIGS, UnitTestInputs.RESULT_FILES
    )
    def test_plot(self):
        """Test whether `vara-plot` generates a plot."""
        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        load_paper_config()
        save_config()
        plot_base_dir = Path(str(vara_cfg()['plots']['plot_dir']))

        # vara-plot
        runner = CliRunner()
        result = runner.invoke(
            driver_plot.main,
            ["--plot-dir=foo", "pc-overview-plot", "--report-type=EmptyReport"]
        )

        self.assertEqual(0, result.exit_code, result.exception)
        self.assertTrue(
            (plot_base_dir / "foo" / "paper_config_overview_plot.svg").exists()
        )

    @run_in_test_environment(UnitTestInputs.PAPER_CONFIGS)
    def test_store_artefact(self):
        """Test whether `vara-plot` can store artefacts."""
        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        load_paper_config()
        save_config()
        artefacts_file_path = get_paper_config().path / "artefacts.yaml"
        artefacts_file_path.unlink()

        # vara-plot
        runner = CliRunner()
        result = runner.invoke(
            driver_plot.main, [
                "--save-artefact=PC Overview", "--plot-dir=foo",
                "pc-overview-plot", "--report-type=EmptyReport"
            ]
        )

        self.assertEqual(0, result.exit_code, result.exception)
        self.assertTrue(artefacts_file_path.exists())

        # load new artefact file
        load_paper_config()
        artefacts = list(get_paper_config().artefacts)
        self.assertEqual(1, len(artefacts))

        artefact = artefacts[0]
        self.assertIsInstance(artefact, PlotArtefact)
        self.assertEqual("PC Overview", artefact.name)
