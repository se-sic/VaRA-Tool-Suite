"""This modules handles auto discovering of tables from the tool suite."""

from varats import tables as __TABLES__

__TABLES_DISCOVERED = False


def initialize_tables() -> None:
    global __TABLES_DISCOVERED  # pylint: disable=global-statement
    if not __TABLES_DISCOVERED:
        # Discover and initialize all plots
        __TABLES__.discover()
        __TABLES_DISCOVERED = True
