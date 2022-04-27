"""Driver module for the case_study generation gui."""
import click

from varats.gui.cs_gen.case_study_generation import start_gui


@click.command("gen-gui")
def main() -> None:
    """Start a gui for generating CaseStudies."""
    start_gui()
