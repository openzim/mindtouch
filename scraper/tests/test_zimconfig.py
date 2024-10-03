import argparse
from unittest import TestCase

from libretexts2zim.entrypoint import add_zim_config_flags
from libretexts2zim.zimconfig import InvalidFormatError, ZimConfig


class TestZimConfig(TestCase):
    def defaults(self) -> ZimConfig:
        return ZimConfig(
            library_name="library-name",
            file_name_format="default_file_name_format",
            name_format="default_name_format",
            title_format="default_title_format",
            publisher="default_publisher",
            creator="default_creator",
            description_format="default_description_format",
            long_description_format="default_long_description_format",
            tags="default_tag1;default_tag2",
            secondary_color="default_secondary-color",
        )

    def test_flag_parsing_defaults(self):
        defaults = self.defaults()
        parser = argparse.ArgumentParser()
        add_zim_config_flags(parser, defaults)

        got = ZimConfig.of(parser.parse_args(args=["--library-name", "library-name"]))

        self.assertEqual(defaults, got)

    def test_flag_parsing_overrides(self):
        parser = argparse.ArgumentParser()
        add_zim_config_flags(parser, self.defaults())

        got = ZimConfig.of(
            parser.parse_args(
                args=[
                    "--library-name",
                    "library-name",
                    "--creator",
                    "creator",
                    "--publisher",
                    "publisher",
                    "--name-format",
                    "name-format",
                    "--file-name-format",
                    "file-name-format",
                    "--title-format",
                    "title-format",
                    "--description-format",
                    "description-format",
                    "--long-description-format",
                    "long-description-format",
                    "--tags",
                    "tag1;tag2",
                    "--secondary-color",
                    "secondary-color",
                ]
            )
        )

        self.assertEqual(
            ZimConfig(
                library_name="library-name",
                creator="creator",
                publisher="publisher",
                name_format="name-format",
                file_name_format="file-name-format",
                title_format="title-format",
                description_format="description-format",
                long_description_format="long-description-format",
                tags="tag1;tag2",
                secondary_color="secondary-color",
            ),
            got,
        )

    def test_format_none_needed(self):
        defaults = self.defaults()

        formatted = defaults.format({})

        self.assertEqual(defaults, formatted)

    def test_format_only_allowed(self):
        to_format = ZimConfig(
            library_name="{replace_me}",
            file_name_format="{replace_me}",
            name_format="{replace_me}",
            title_format="{replace_me}",
            publisher="{replace_me}",
            creator="{replace_me}",
            description_format="{replace_me}",
            long_description_format="{replace_me}",
            tags="{replace_me}",
            secondary_color="{replace_me}",
        )

        got = to_format.format({"replace_me": "replaced"})

        self.assertEqual(
            ZimConfig(
                library_name="{replace_me}",
                file_name_format="replaced",
                name_format="replaced",
                title_format="replaced",
                publisher="{replace_me}",
                creator="{replace_me}",
                description_format="replaced",
                long_description_format="replaced",
                tags="replaced",
                secondary_color="{replace_me}",
            ),
            got,
        )

    def test_format_long_title_fails(self):
        to_format = self.defaults()
        to_format.title_format = "a" * 10000

        self.assertRaises(ValueError, to_format.format, {})

    def test_format_long_description_fails(self):
        to_format = self.defaults()
        to_format.description_format = "a" * 10000

        self.assertRaises(ValueError, to_format.format, {})

    def test_format_long_long_description_fails(self):
        to_format = self.defaults()
        to_format.long_description_format = "a" * 10000

        self.assertRaises(ValueError, to_format.format, {})

    def test_format_invalid(self):
        to_format = self.defaults()
        to_format.name_format = "{invalid_placeholder}"

        self.assertRaises(
            InvalidFormatError, to_format.format, {"valid1": "", "valid2": ""}
        )
