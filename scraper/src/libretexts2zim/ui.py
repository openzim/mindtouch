from humps import camelize
from pydantic import BaseModel, ConfigDict


class CamelModel(BaseModel):
    """Model to transform Python snake_case into JSON camelCase."""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)


class PageModel(CamelModel):
    id: str
    title: str
    path: str


class PageContentModel(CamelModel):
    html_body: str


class SharedModel(CamelModel):
    logo_path: str
    root_page_path: str
    pages: list[PageModel]


class ConfigModel(CamelModel):
    secondary_color: str
