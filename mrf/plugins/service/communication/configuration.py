"""Spring configuration of one service, as far as a placeholder needs it.

A client states the address of the service it calls as a placeholder more often
than as a literal, and the value behind it is in the service's own
configuration. This module reads that configuration and resolves a placeholder
against it.

Only the service's own ``application*.properties`` and ``application*.yml`` are
read. The deployment overrides the host - Lakeside Mutual's Compose file sets
``CUSTOMERCORE_BASEURL`` - but not the scheme, and the scheme is what this phase
reconstructs, so the deployment is left to the step that needs the host (see
ADR-0009).
"""

import logging
from dataclasses import dataclass, field
from pathlib import PurePath

import yaml

from mrf.utilities.command_line import SourceFile
from mrf.utilities.communication import (
    APPLICATION_PREFIX,
    MAIN_RESOURCES,
    PLACEHOLDER_DEFAULT_SEPARATOR,
    PLACEHOLDER_PREFIX,
    PLACEHOLDER_SUFFIX,
    PROPERTIES_SUFFIX,
    YAML_SUFFIXES,
)

logger = logging.getLogger(__name__)

SOURCE_ROOT = "src/main/java"
SERVER_PORT = "server.port"
APPLICATION_NAME = "spring.application.name"


@dataclass
class ServiceConfiguration:
    """Configuration of one service, by property name.

    Attributes:
        module: Root directory of the service, the part of a path above
            ``src/main/java``
        properties: Values of the default configuration, by property name
        profile_properties: Values of each profile-specific configuration, by
            profile name
        origins: File a property was read from, by property name
    """

    module: str
    properties: dict[str, str] = field(default_factory=dict)
    profile_properties: dict[str, dict[str, str]] = field(default_factory=dict)
    origins: dict[str, str] = field(default_factory=dict)

    @property
    def server_port(self) -> str | None:
        """Port the service listens on, or ``None`` when it is not configured."""
        return self.properties.get(SERVER_PORT)

    @property
    def application_name(self) -> str | None:
        """Name the service registers under, or ``None``."""
        return self.properties.get(APPLICATION_NAME)

    def resolve(self, placeholder: str) -> tuple[str | None, str | None, str | None]:
        """Resolve a placeholder against this configuration.

        The default configuration is read first, then each profile. A profile
        that states a different value yields a result of its own, so a caller
        can report one fact per profile.

        Args:
            placeholder: Text of the placeholder, with or without ``${}``

        Returns:
            The resolved value, the profile it was resolved for - ``None`` for
            the default configuration - and the property name. The value is
            ``None`` when nothing defines the property and the placeholder
            names no default.
        """
        name, default = split_placeholder(placeholder)
        if name in self.properties:
            return self.properties[name], None, name

        for profile in sorted(self.profile_properties):
            if name in self.profile_properties[profile]:
                return self.profile_properties[profile][name], profile, name

        return default, None, name


def split_placeholder(placeholder: str) -> tuple[str, str | None]:
    """Split a placeholder into its property name and its default value.

    ``${customercore.baseURL}`` has no default, ``${url:http://localhost}`` has
    one. A URL as the default holds a colon of its own, so only the first one
    separates.

    Args:
        placeholder: Text of the placeholder, with or without ``${}``

    Returns:
        The property name and the default value, or ``None`` when there is none
    """
    text = placeholder.strip()
    if text.startswith(PLACEHOLDER_PREFIX) and text.endswith(PLACEHOLDER_SUFFIX):
        text = text[len(PLACEHOLDER_PREFIX) : -len(PLACEHOLDER_SUFFIX)]
    name, separator, default = text.partition(PLACEHOLDER_DEFAULT_SEPARATOR)
    if not separator:
        return name.strip(), None
    return name.strip(), default.strip()


def is_placeholder(value: str) -> bool:
    """Check whether a value is a single placeholder rather than a literal."""
    text = value.strip()
    return text.startswith(PLACEHOLDER_PREFIX) and text.endswith(PLACEHOLDER_SUFFIX)


def module_of(path: str) -> str | None:
    """Return the root directory of the service a file belongs to.

    A Maven or Gradle module keeps its sources under ``src/main/java``, so what
    lies above it is the service. A file outside such a layout belongs to no
    module.

    Args:
        path: Path of a file of the service

    Returns:
        The module's directory, or ``None``
    """
    posix = PurePath(path).as_posix()
    index = posix.find(SOURCE_ROOT)
    if index < 0:
        index = posix.find(MAIN_RESOURCES)
    if index < 0:
        return None
    return posix[:index].rstrip("/")


def read_configurations(
    source_files: list[SourceFile],
) -> dict[str, ServiceConfiguration]:
    """Read the Spring configuration of every service of the analysed system.

    Args:
        source_files: Source files of the analysed system

    Returns:
        The configuration of each service, by the service's module directory
    """
    configurations: dict[str, ServiceConfiguration] = {}
    for source_file in sorted(source_files, key=lambda f: f.path):
        if source_file.file is None:
            continue
        name = PurePath(source_file.path).name
        if not name.startswith("application"):
            continue
        module = module_of(source_file.path)
        if module is None:
            continue

        configuration = configurations.setdefault(module, ServiceConfiguration(module))
        values = __read(source_file)
        if not values:
            continue

        profile = __profile_of(name)
        if profile is None:
            configuration.properties.update(values)
            for key in values:
                configuration.origins[key] = source_file.path
        else:
            configuration.profile_properties.setdefault(profile, {}).update(values)
            for key in values:
                configuration.origins.setdefault(f"{profile}:{key}", source_file.path)

    return configurations


def __profile_of(file_name: str) -> str | None:
    """Return the profile a configuration file belongs to, or ``None``."""
    if not file_name.startswith(APPLICATION_PREFIX):
        return None
    rest = file_name[len(APPLICATION_PREFIX) :]
    for suffix in [PROPERTIES_SUFFIX, *YAML_SUFFIXES]:
        if rest.endswith(suffix):
            return rest[: -len(suffix)]
    return None


def __read(source_file: SourceFile) -> dict[str, str]:
    name = PurePath(source_file.path).name
    if name.endswith(PROPERTIES_SUFFIX):
        return __read_properties(source_file.file or "")
    if any(name.endswith(suffix) for suffix in YAML_SUFFIXES):
        return __read_yaml(source_file)
    return {}


def __read_properties(content: str) -> dict[str, str]:
    """Read a properties file, ignoring comments and lines without a value."""
    values: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator:
            continue
        values[key.strip()] = value.strip()
    return values


def __read_yaml(source_file: SourceFile) -> dict[str, str]:
    """Read a YAML configuration, flattened to the property names Spring uses."""
    try:
        documents = list(yaml.safe_load_all(source_file.file or ""))
    except yaml.YAMLError:
        logger.warning("Skipping %s, it is no valid YAML.", source_file.path)
        return {}

    values: dict[str, str] = {}
    for document in documents:
        if isinstance(document, dict):
            values.update(__flatten(document, ""))
    return values


def __flatten(mapping: dict, prefix: str) -> dict[str, str]:
    """Flatten a nested mapping into the dotted property names Spring reads."""
    values: dict[str, str] = {}
    for key, value in mapping.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            values.update(__flatten(value, f"{name}."))
        elif value is not None and not isinstance(value, list):
            values[name] = str(value)
    return values
