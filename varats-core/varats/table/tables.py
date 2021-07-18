"""General tables module."""
import logging
import re
import typing as tp
from pathlib import Path

from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.plot.plot_utils import check_required_args
from varats.utils.settings import vara_cfg

if tp.TYPE_CHECKING:
    from varats.table import table  # pylint: disable=unused-import

LOG = logging.getLogger(__name__)


class TableRegistry(type):
    """Registry for all supported tables."""

    TO_SNAKE_CASE_PATTERN = re.compile(r'(?<!^)(?=[A-Z])')

    tables: tp.Dict[str, tp.Type[tp.Any]] = {}
    tables_discovered = False

    def __init__(
        cls, name: str, bases: tp.Tuple[tp.Any], attrs: tp.Dict[tp.Any, tp.Any]
    ):
        super(TableRegistry, cls).__init__(name, bases, attrs)
        if hasattr(cls, 'NAME'):
            key = getattr(cls, 'NAME')
        else:
            key = TableRegistry.TO_SNAKE_CASE_PATTERN.sub('_', name).lower()
        TableRegistry.tables[key] = cls

    @staticmethod
    def get_table_types_help_string() -> str:
        """
        Generates help string for visualizing all available tables.

        Returns:
            a help string that contains all available table names.
        """
        return "The following tables are available:\n  " + "\n  ".join([
            key for key in TableRegistry.tables if key != "table"
        ])

    @staticmethod
    def get_class_for_table_type(table_type: str) -> tp.Type['table.Table']:
        """
        Get the class for ``table`` from the table registry.

        Args:
            table_type: the name of the table

        Returns:
            the class implementing the table
        """
        from varats.table.table import Table  # pylint: disable=C0415
        if table_type not in TableRegistry.tables:
            raise LookupError(
                f"Unknown table '{table_type}'.\n" +
                TableRegistry.get_table_types_help_string()
            )

        table_cls = TableRegistry.tables[table_type]
        if not issubclass(table_cls, Table):
            raise AssertionError()
        return table_cls


def build_tables(**args: tp.Any) -> None:
    """
    Build the specfied table(s).

    Args:
        **args: the arguments for the table(s)
    """
    for p_table in prepare_tables(**args):
        build_table(p_table)


def build_table(table_to_build: 'table.Table') -> None:
    """
    Builds the given table.

    Args:
        table: the table to build
    """
    table_to_build.format = table_to_build.table_kwargs["output-format"]
    if table_to_build.table_kwargs["view"]:
        print(table_to_build.tabulate())
    else:
        table_to_build.save(
            wrap_document=table_to_build.table_kwargs.
            get("wrap_document", False)
        )


@check_required_args(['table_type'])
def prepare_table(**kwargs: tp.Any) -> 'table.Table':
    """
    Instantiate a table with the given args.

    Args:
        **kwargs: the arguments for the table

    Returns:
        the instantiated table
    """
    table_type = TableRegistry.get_class_for_table_type(kwargs['table_type'])
    return table_type(**kwargs)


def prepare_tables(**args: tp.Any) -> tp.Iterable['table.Table']:
    """
    Instantiate the specified table(s).

    First, compute missing arguments that are needed by most tables.

    Args:
        **args: the arguments for the table(s)

    Returns:
        an iterable of instantiated table
    """
    # pylint: disable=C0415
    from varats.paper.case_study import load_case_study_from_file
    from varats.paper_mgmt.paper_config import get_paper_config
    # pylint: enable=C0415

    # Setup default result folder
    if 'result_output' not in args:
        args['table_dir'] = str(vara_cfg()['tables']['table_dir'])
    else:
        args['table_dir'] = args.pop('result_output')

    if not Path(args['table_dir']).exists():
        LOG.error(f"Could not find output dir {args['table_dir']}")
        return []

    if 'view' not in args:
        args['view'] = False
    if 'output-format' not in args:
        from varats.table.table import TableFormat  # pylint: disable=C0415
        if args['view']:
            args['output-format'] = TableFormat.FANCY_GRID
        else:
            args['output-format'] = TableFormat.LATEX_BOOKTABS
    if 'paper_config' not in args:
        args['paper_config'] = False

    LOG.info(f"Writing tables to: {args['table_dir']}")

    if args['paper_config']:
        tables: tp.List['table.Table'] = []
        paper_config = get_paper_config()
        for case_study in paper_config.get_all_case_studies():
            project_name = case_study.project_name
            args['project'] = project_name
            args['get_cmap'] = create_lazy_commit_map_loader(project_name)
            args['table_case_study'] = case_study
            tables.append(prepare_table(**args))
        return tables

    if 'project' in args:
        args['get_cmap'] = create_lazy_commit_map_loader(args['project'])
    if 'cs_path' in args:
        case_study_path = Path(args['cs_path'])
        args['table_case_study'] = load_case_study_from_file(case_study_path)
    else:
        args['table_case_study'] = None

    return [prepare_table(**args)]
