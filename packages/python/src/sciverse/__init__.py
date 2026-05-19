"""Sciverse Agent Tools - Python SDK."""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

from sciverse.client import AgentToolsClient
from sciverse.credentials import (
    credentials_path,
    delete_credentials,
    load_credentials,
    resolve_endpoint,
    resolve_token,
    save_credentials,
)
from sciverse.tools import OPENAI_TOOLS, ANTHROPIC_TOOLS, TOOLS_VERSION

try:
    __version__ = _pkg_version("sciverse")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "AgentToolsClient",
    "OPENAI_TOOLS",
    "ANTHROPIC_TOOLS",
    "TOOLS_VERSION",
    "credentials_path",
    "delete_credentials",
    "load_credentials",
    "resolve_endpoint",
    "resolve_token",
    "save_credentials",
]
