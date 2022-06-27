"""Test varats container support module."""
import typing as tp
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory

from benchbuild.environments.adapters.common import buildah_version
from benchbuild.environments.domain.model import (
    Layer,
    FromLayer,
    WorkingDirectory,
    CopyLayer,
    UpdateEnv,
    RunLayer,
    EntryPoint,
)

from tests.test_utils import run_in_test_environment
from varats.containers.containers import (
    ImageBase,
    BaseImageCreationContext,
    _create_base_image_layers,
    _create_dev_image_layers,
)
from varats.tools.research_tools.research_tool import Distro
from varats.tools.tool_util import get_research_tool
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
        """Test base image creation."""
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

        varats_install_layer = self.check_layer_type(layers[10], RunLayer)
        self.assertEqual("pip3", varats_install_layer.command)
        self.assertTupleEqual(
            ("install", '--ignore-installed', "varats-core", "varats"),
            varats_install_layer.args
        )

        varats_copy_config_layer = self.check_layer_type(layers[11], CopyLayer)
        self.assertEqual(
            "/varats_root/.varats.yaml", varats_copy_config_layer.destination
        )

        varats_config_layer = self.check_layer_type(layers[12], UpdateEnv)
        self.assertTupleEqual(
            ("VARATS_CONFIG_FILE", "/varats_root/.varats.yaml"),
            varats_config_layer.env[0]
        )

        bb_config_layer = self.check_layer_type(layers[13], UpdateEnv)
        self.assertTupleEqual(("BB_VARATS_OUTFILE", "/varats_root/results"),
                              bb_config_layer.env[0])
        self.assertTupleEqual(("BB_VARATS_RESULT", "/varats_root/BC_files"),
                              bb_config_layer.env[1])
        self.assertTupleEqual(("BB_JOBS", "42"), bb_config_layer.env[2])
        self.assertTupleEqual(("BB_ENV", "{}"), bb_config_layer.env[3])

        cwd_layer = self.check_layer_type(layers[14], WorkingDirectory)
        self.assertEqual("/app", cwd_layer.directory)

    @run_in_test_environment()
    def test_create_base_image_from_source(self) -> None:
        """Test varats install from source."""
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

        varats_install_layer = self.check_layer_type(layers[12], RunLayer)
        self.assertEqual("pip3", varats_install_layer.command)
        self.assertTupleEqual((
            "install", "--ignore-installed", "/varats/varats-core",
            "/varats/varats"
        ), varats_install_layer.args)
        mounting_parameters = "type=bind,src=varats_src,target=/varats"
        if buildah_version() >= (1, 24, 0):
            mounting_parameters += ",rm"
        self.assertIn(("mount", mounting_parameters),
                      varats_install_layer.kwargs)

    @run_in_test_environment()
    def test_ld_library_path(self) -> None:
        """Test mapping of LD_LIBRARY_PATH into container."""
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
        ld_copy_layer = self.check_layer_type(layers[13], CopyLayer)
        self.assertEqual("/varats_root/libs", ld_copy_layer.destination)
        self.assertTupleEqual(("foo/libs",), ld_copy_layer.sources)

        bb_config_layer = self.check_layer_type(layers[14], UpdateEnv)
        self.assertTupleEqual(
            ("BB_ENV", "{LD_LIBRARY_PATH: [/varats_root/libs]}"),
            bb_config_layer.env[3]
        )

    @run_in_test_environment()
    @mock.patch("varats.tools.research_tools.vara.VaRA.install_exists")
    def test_vara_install(self, mock_install_exists) -> None:
        """Test VaRA install inside container."""
        mock_install_exists.return_value = True
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
        vara_deps_layer = self.check_layer_type(layers[11], RunLayer)
        self.assertEqual("apt", vara_deps_layer.command)

        vara_copy_layer = self.check_layer_type(layers[12], CopyLayer)
        self.assertEqual(
            "/varats_root/tools/VaRA_DEBIAN_10", vara_copy_layer.destination
        )
        self.assertTupleEqual(("tools/VaRA_DEBIAN_10",),
                              vara_copy_layer.sources)

        bb_config_layer = self.check_layer_type(layers[15], UpdateEnv)
        self.assertTupleEqual(
            ("BB_ENV", "{PATH: [/varats_root/tools/VaRA_DEBIAN_10/bin]}"),
            bb_config_layer.env[3]
        )

    @run_in_test_environment()
    def test_create_dev_image(self) -> None:
        """Test VaRA install inside container."""
        vara_cfg()["vara"]["llvm_source_dir"] = "tools_src/vara-llvm-project"
        vara_cfg()["vara"]["llvm_install_dir"] = "tools/VaRA"
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False

        with TemporaryDirectory() as tmpdir:
            research_tool = get_research_tool("vara")
            image_context = BaseImageCreationContext(
                ImageBase.DEBIAN_10, Path(tmpdir)
            )
            _create_dev_image_layers(image_context, research_tool)

        layers = image_context.layers

        # check that varats will be installed properly
        varats_install_layer = self.check_layer_type(layers[10], RunLayer)
        self.assertEqual("pip3", varats_install_layer.command)
        self.assertTupleEqual(
            ("install", '--ignore-installed', "varats-core", "varats"),
            varats_install_layer.args
        )
        varats_copy_config_layer = self.check_layer_type(layers[12], CopyLayer)
        self.assertEqual(
            "/varats_root/.varats.yaml", varats_copy_config_layer.destination
        )

        # check that research tool dependencies will be installed
        vara_deps_layer = self.check_layer_type(layers[11], RunLayer)
        self.assertEqual("apt", vara_deps_layer.command)

        # check that correct entry point will be set
        entrypoint_layer = self.check_layer_type(layers[16], EntryPoint)
        self.assertEqual(("vara-buildsetup",), entrypoint_layer.command)

    LayerTy = tp.TypeVar("LayerTy", bound=Layer)

    def check_layer_type(
        self, layer: Layer, layer_ty: tp.Type[LayerTy]
    ) -> LayerTy:
        self.assertTrue(isinstance(layer, layer_ty))
        return layer
