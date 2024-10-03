import argparse

from pydantic import BaseModel
from zimscraperlib.constants import (
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)


class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class ZimConfig(BaseModel):
    """Common configuration for building ZIM files."""

    # Displayable name for library, e.g. Geosciences
    library_name: str
    # File name for the ZIM.
    file_name_format: str
    # Name for the ZIM.
    name_format: str
    # Human readable title for the ZIM.
    title_format: str
    # Publisher for the ZIM.
    publisher: str
    # Creator of the content in the ZIM.
    creator: str
    # Short description for the ZIM.
    description_format: str
    # Long description for the ZIM.
    long_description_format: str | None
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

        def check_length(string: str, field_name: str, length: int) -> str:
            if len(string) > length:
                raise ValueError(
                    f"{field_name} '{string[:15]}…' ({len(string)} chars) "
                    f"is longer than the allowed {length} chars"
                )

            return string

        return ZimConfig(
            secondary_color=self.secondary_color,
            library_name=self.library_name,
            file_name_format=fmt(self.file_name_format),
            name_format=fmt(self.name_format),
            title_format=check_length(
                fmt(self.title_format),
                "formatted title",
                RECOMMENDED_MAX_TITLE_LENGTH,
            ),
            publisher=self.publisher,
            creator=self.creator,
            description_format=check_length(
                fmt(self.description_format),
                "formatted description",
                MAXIMUM_DESCRIPTION_METADATA_LENGTH,
            ),
            long_description_format=(
                check_length(
                    fmt(self.long_description_format),
                    "formatted long description",
                    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
                )
                if self.long_description_format
                else None
            ),
            tags=fmt(self.tags),
        )
