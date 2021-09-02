"""Project domain module that defines different project domains."""

from enum import Enum


class ProjectDomains(Enum):
    """Defines a set of project domains."""
    value: str

    COMPRESSION = "Compression"
    UNIX_TOOLS = "UNIX utils"
    DATABASE = "Database"
    HW_EMULATOR = "Hardware emulator"
    CODEC = "Codec"
    FILE_FORMAT = "File format"
    CHAT_CLIENT = "Chat client"
    DATA_STRUCTURES = "Data structures"
    PROG_LANG = "Programming language"
    PROTOCOL = "Protocol"
    PARSER = "Parser"
    WEB_TOOLS = "Web tools"
    VERSION_CONTROL = "Version control"
    C_LIBRARY = "C Library"
    SIGNAL_PROCESSING = "Signal processing"
    SECURITY = "Security"
    EDITOR = "Editor"
    ENCODER = "Encoder"
    TEST = "Test project"
    RENDERING = "Rendering"
    DOCUMENTATION = "Documentation"

    def __str__(self) -> str:
        return self.value
