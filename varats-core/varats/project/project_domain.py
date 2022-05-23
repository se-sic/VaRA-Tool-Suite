"""Project domain module that defines different project domains."""

from enum import Enum


class ProjectDomains(Enum):
    """Defines a set of project domains."""
    value: str

    CHAT_CLIENT = "Chat client"
    CODEC = "Codec"
    COMPRESSION = "Compression"
    C_LIBRARY = "C Library"
    DATABASE = "Database"
    DATA_STRUCTURES = "Data structures"
    DOCUMENTATION = "Documentation"
    EDITOR = "Editor"
    FILE_FORMAT = "File format"
    HW_EMULATOR = "Hardware emulator"
    PARSER = "Parser"
    PROG_LANG = "Programming language"
    PROTOCOL = "Protocol"
    RENDERING = "Rendering"
    SECURITY = "Security"
    SIGNAL_PROCESSING = "Signal processing"
    TEST = "Test project"
    UNIX_TOOLS = "UNIX utils"
    VERSION_CONTROL = "Version control"
    WEB_TOOLS = "Web tools"

    def __str__(self) -> str:
        return str(self.value)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, ProjectDomains):
            return self.value < other.value

        return False


class ProjectGroups(Enum):
    """Defines a set of project groups."""
    value: str

    C_PROJECTS = "c_projects"
    CPP_PROJECTS = "cpp_projects"

    def __str__(self) -> str:
        return str(self.value)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, ProjectGroups):
            return self.value < other.value

        return False
