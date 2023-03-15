"""Module for table related utility functionality."""

import typing as tp

import pandas as pd
from pylatex import Document, Package, NoEscape
from tabulate import tabulate

from varats.table.tables import TableFormat


def wrap_table_in_latex_document(
    table: str, landscape: bool = False, margin: float = 1.5
) -> str:
    """
    Wraps a table inside a proper latex document.

    Uses ``\\longtable`` instead of ``\\tabular`` to fit data on multiple pages.

    Args:
        table: table string to wrap the document around
        landscape: whether to layout the table in landscape mode
        margin: margin around the table in cm

    Returns:
        the resulting latex document as a string
    """
    doc = Document(
        documentclass="scrbook",
        document_options="paper=a4",
        geometry_options={
            "margin": f"{margin}cm",
            "landscape": "true" if landscape else "false"
        }
    )

    doc.packages.update([
        Package("booktabs"),
        Package("hyperref"),
        Package("longtable"),
        Package("multirow"),
        Package("xcolor", options=["table"]),
    ])

    doc.change_document_style("empty")

    # embed latex table inside document
    doc.append(NoEscape(table))

    return tp.cast(str, doc.dumps())


def dataframe_to_table(
    data: pd.DataFrame,
    table_format: TableFormat,
    style: tp.Optional["pd.io.formats.style.Styler"] = None,
    wrap_table: bool = False,
    wrap_landscape: bool = False,
    **kwargs: tp.Any
) -> str:
    """
    Convert a pandas ``DataFrame`` to a table.

    Args:
        data: the ``DataFrame`` to convert
        table_format: the table format used for conversion
        style: optional styler object;
               needs to be passed when custom styles are used
        wrap_table: whether to wrap the table in a separate
                    document (latex only)
        wrap_landscape: whether to use landscape mode to wrap the
                        table (latex only)
        **kwargs: kwargs that get passed to pandas' conversion functions
                  (``DataFrame.to_latex`` or ``DataFrame.to_html``)

    Returns:
        the table as a string
    """
    table = ""
    if not style:
        style = data.style
    if table_format.is_latex():
        table = style.to_latex(**kwargs)
        if wrap_table:
            table = wrap_table_in_latex_document(table, wrap_landscape)

    elif table_format.is_html():
        table = style.to_html(**kwargs)
    else:
        table = tabulate(data, data.columns, table_format.value)

    return table
