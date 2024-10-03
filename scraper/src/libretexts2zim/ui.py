from humps import camelize
from pydantic import BaseModel, ConfigDict


class CamelModel(BaseModel):
    """Model to transform Python snake_case into JSON camelCase."""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)


class HomeModel(CamelModel):
    welcome_text_paragraphs: list[str]


class SharedModel(CamelModel):
    logo_path: str


class ConfigModel(CamelModel):
    secondary_color: str
