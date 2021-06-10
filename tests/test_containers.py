"""Test varats container support module."""
import typing as tp
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory

from benchbuild.environments.domain.model import (
    Layer,
    FromLayer,
    WorkingDirectory,
    CopyLayer,
    UpdateEnv,
    RunLayer,
)

from tests.test_utils import run_in_test_environment
from varats.containers.containers import (
    ImageBase,
    BaseImageCreationContext,
    _create_base_image_layers,
)
from varats.tools.research_tools.research_tool import Distro
from varats.utils.settings import vara_cfg, bb_cfg


class TestImageBase(unittest.TestCase):
    """Test ImageBase class."""

    @run_in_test_environment()
    def test_image_name_no_tool(self):
        vara_cfg()["container"]["research_tool"] = None
        self.assertEqual(
            "localhost/debian:10_varats", ImageBase.DEBIAN_10.image_name
        )

    @run_in_test_environment()
    def test_image_name_vara(self):
        vara_cfg()["container"]["research_tool"] = "vara"
        self.assertEqual(
            "localhost/debian:10_varats_vara", ImageBase.DEBIAN_10.image_name
        )

    def test_distro(self):
        self.assertEqual(Distro.DEBIAN, ImageBase.DEBIAN_10.distro)


class TestContainerSupport(unittest.TestCase):
    """Test container support related functionality."""

    @run_in_test_environment()
    def test_create_base_image(self):
        """Test function with mocked method for file access."""
        vara_cfg()["container"]["research_tool"] = None
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False
        bb_cfg()["jobs"] = 42

        with TemporaryDirectory() as tmpdir:
            image_context = BaseImageCreationContext(
                ImageBase.DEBIAN_10, Path(tmpdir)
            )
            _create_base_image_layers(image_context)

        layers = image_context.layers
        self.check_layer_type(layers[0], FromLayer)

        varats_install_layer = self.check_layer_type(layers[4], RunLayer)
        self.assertEqual("pip3", varats_install_layer.command)
        self.assertTupleEqual(("install", "varats-core", "varats"),
                              varats_install_layer.args)

        varats_copy_config_layer = self.check_layer_type(layers[5], CopyLayer)
        self.assertEqual(
            "/varats_root/.varats.yaml", varats_copy_config_layer.destination
        )

        varats_config_layer = self.check_layer_type(layers[6], UpdateEnv)
        self.assertTupleEqual(
            ("VARATS_CONFIG_FILE", "/varats_root/.varats.yaml"),
            varats_config_layer.env[0]
        )

        bb_config_layer = self.check_layer_type(layers[7], UpdateEnv)
        self.assertTupleEqual(("BB_VARATS_OUTFILE", "/varats_root/results"),
                              bb_config_layer.env[0])
        self.assertTupleEqual(("BB_VARATS_RESULT", "/varats_root/BC_files"),
                              bb_config_layer.env[1])
        self.assertTupleEqual(("BB_JOBS", "42"), bb_config_layer.env[2])
        self.assertTupleEqual(("BB_ENV", "{}"), bb_config_layer.env[3])

        cwd_layer = self.check_layer_type(layers[8], WorkingDirectory)
        self.assertEqual("/app", cwd_layer.directory)

    @run_in_test_environment()
    def test_create_base_image(self) -> None:
        """Test function with mocked method for file access."""
        vara_cfg()["container"]["research_tool"] = None
        vara_cfg()["container"]["from_source"] = True
        vara_cfg()["container"]["varats_source"] = "varats_src"
        bb_cfg()["container"]["from_source"] = False
        bb_cfg()["jobs"] = 42

        with TemporaryDirectory() as tmpdir:
            image_context = BaseImageCreationContext(
                ImageBase.DEBIAN_10, Path(tmpdir)
            )
            _create_base_image_layers(image_context)

        layers = image_context.layers

        varats_install_layer = self.check_layer_type(layers[6], RunLayer)
        self.assertEqual("pip3", varats_install_layer.command)
        self.assertTupleEqual((
            "install", "--ignore-installed", "/varats/varats-core",
            "/varats/varats"
        ), varats_install_layer.args)
        self.assertIn(("mount", "type=bind,src=varats_src,target=/varats"),
                      varats_install_layer.kwargs)

    @run_in_test_environment()
    def test_ld_library_path(self) -> None:
        vara_cfg()["container"]["research_tool"] = None
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False
        bb_cfg()["env"] = {
            "LD_LIBRARY_PATH": ["foo/libs"],
            "PATH": ["/foo/bin"]
        }

        with TemporaryDirectory() as tmpdir:
            image_context = BaseImageCreationContext(
                ImageBase.DEBIAN_10, Path(tmpdir)
            )
            _create_base_image_layers(image_context)

        layers = image_context.layers
        ld_copy_layer = self.check_layer_type(layers[7], CopyLayer)
        self.assertEqual("/varats_root/libs", ld_copy_layer.destination)
        self.assertTupleEqual(("foo/libs",), ld_copy_layer.sources)

        bb_config_layer = self.check_layer_type(layers[8], UpdateEnv)
        self.assertTupleEqual(
            ("BB_ENV", "{LD_LIBRARY_PATH: [/varats_root/libs]}"),
            bb_config_layer.env[3]
        )

    @run_in_test_environment()
    @mock.patch("varats.tools.research_tools.vara.VaRA.verify_install")
    def test_vara_install(self, mock_verify_install) -> None:
        mock_verify_install.return_value = True
        vara_cfg()["container"]["research_tool"] = "vara"
        vara_cfg()["vara"]["llvm_source_dir"] = "tools_src/vara-llvm-project"
        vara_cfg()["vara"]["llvm_install_dir"] = "tools/VaRA"
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False

        with TemporaryDirectory() as tmpdir:
            image_context = BaseImageCreationContext(
                ImageBase.DEBIAN_10, Path(tmpdir)
            )
            _create_base_image_layers(image_context)

        layers = image_context.layers
        vara_copy_layer = self.check_layer_type(layers[5], CopyLayer)
        self.assertEqual("/varats_root/tools/VaRA", vara_copy_layer.destination)
        self.assertTupleEqual(("tools/VaRA",), vara_copy_layer.sources)

        bb_config_layer = self.check_layer_type(layers[8], UpdateEnv)
        self.assertTupleEqual(
            ("BB_ENV", "{PATH: [/varats_root/tools/VaRA/bin]}"),
            bb_config_layer.env[3]
        )

    LayerTy = tp.TypeVar("LayerTy", bound=Layer)

    def check_layer_type(
        self, layer: Layer, layer_ty: tp.Type[LayerTy]
    ) -> LayerTy:
        self.assertTrue(isinstance(layer, layer_ty))
        return layer
