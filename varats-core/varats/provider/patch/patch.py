from pathlib import Path
import typing as tp


class Patch:
    """A class for storing a project-specific Patch"""
    project: str
    shortname: str
    description: str
    path: Path
    revisions: tp.List[str]
