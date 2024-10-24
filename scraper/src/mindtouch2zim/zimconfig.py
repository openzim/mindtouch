import argparse

from pydantic import BaseModel


class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class ZimConfig(BaseModel):
    """Common configuration for building ZIM files."""

    # File name for the ZIM.
    file_name: str
    # Name for the ZIM.
    name: str
    # Human readable title for the ZIM.
    title: str
    # Publisher for the ZIM.
    publisher: str
    # Creator of the content in the ZIM.
    creator: str
    # Short description for the ZIM.
    description: str
    # Long description for the ZIM.
    long_description: str | None
    # Semicolon delimited list of tags to apply to the ZIM.
    tags: str
    # Secondary (background) color of ZIM UI
    secondary_color: str

    @staticmethod
    def of(namespace: argparse.Namespace) -> "ZimConfig":
        """Parses a namespace to create a new ZimConfig."""
        return ZimConfig.model_validate(namespace, from_attributes=True)

    def format(self, placeholders: dict[str, str]) -> "ZimConfig":
        """Creates a ZimConfig with placeholders replaced and results checked.

        Raises:
          InvalidFormatError if one of the placeholders is invalid.
          ValueError if formatted value is too long (when restricted).
        """

        def fmt(string: str) -> str:
            try:
                return string.format(**placeholders)
            except KeyError as e:
                valid_placeholders = ", ".join(sorted(placeholders.keys()))
                raise InvalidFormatError(
                    f"Invalid placeholder {e!s} in {string!r}, "
                    f"valid placeholders are: {valid_placeholders}"
                ) from e

        return ZimConfig(
            secondary_color=self.secondary_color,
            file_name=fmt(self.file_name),
            name=fmt(self.name),
            title=fmt(self.title),
            publisher=self.publisher,
            creator=self.creator,
            description=fmt(self.description),
            long_description=(
                fmt(self.long_description) if self.long_description else None
            ),
            tags=fmt(self.tags),
        )
