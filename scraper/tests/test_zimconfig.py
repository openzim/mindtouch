import argparse
from unittest import TestCase

from mindtouch2zim.entrypoint import add_zim_config_flags
from mindtouch2zim.zimconfig import InvalidFormatError, ZimConfig


class TestZimConfig(TestCase):
    def defaults(self) -> ZimConfig:
        return ZimConfig(
            file_name="default_file_name_format",
            name="default_name_format",
            title="default_title_format",
            publisher="default_publisher",
            creator="default_creator",
            description="default_description_format",
            long_description="default_long_description_format",
            tags="default_tag1;default_tag2",
            secondary_color="default_secondary-color",
        )

    def test_flag_parsing_defaults(self):
        defaults = self.defaults()
        parser = argparse.ArgumentParser()
        add_zim_config_flags(parser, defaults)

        got = ZimConfig.of(
            parser.parse_args(
                args=[
                    "--name",
                    "tests_en_library",
                    "--creator",
                    "bob",
                    "--title",
                    "a title",
                    "--description",
                    "a description",
                ]
            )
        )

        self.assertEqual(
            ZimConfig(
                creator="bob",
                publisher=defaults.publisher,
                name="tests_en_library",
                file_name=defaults.file_name,
                title="a title",
                description="a description",
                long_description=defaults.long_description,
                tags=defaults.tags,
                secondary_color=defaults.secondary_color,
            ),
            got,
        )

    def test_flag_parsing_overrides(self):
        parser = argparse.ArgumentParser()
        add_zim_config_flags(parser, self.defaults())

        got = ZimConfig.of(
            parser.parse_args(
                args=[
                    "--creator",
                    "creator",
                    "--publisher",
                    "publisher",
                    "--name",
                    "tests_en_aname",
                    "--file-name",
                    "tests_en_aname_{period}",
                    "--title",
                    "a title",
                    "--description",
                    "a description",
                    "--long-description",
                    "a long description",
                    "--tags",
                    "tag1;tag2",
                    "--secondary-color",
                    "#FAFAFA",
                ]
            )
        )

        self.assertEqual(
            ZimConfig(
                creator="creator",
                publisher="publisher",
                name="tests_en_aname",
                file_name="tests_en_aname_{period}",
                title="a title",
                description="a description",
                long_description="a long description",
                tags="tag1;tag2",
                secondary_color="#FAFAFA",
            ),
            got,
        )

    def test_format_none_needed(self):
        defaults = self.defaults()

        formatted = defaults.format({})

        self.assertEqual(defaults, formatted)

    def test_format_only_allowed(self):
        to_format = ZimConfig(
            file_name="{replace_me}",
            name="{replace_me}",
            title="{replace_me}",
            publisher="{replace_me}",
            creator="{replace_me}",
            description="{replace_me}",
            long_description="{replace_me}",
            tags="{replace_me}",
            secondary_color="{replace_me}",
        )

        got = to_format.format({"replace_me": "replaced"})

        self.assertEqual(
            ZimConfig(
                file_name="replaced",
                name="replaced",
                title="replaced",
                publisher="{replace_me}",
                creator="{replace_me}",
                description="replaced",
                long_description="replaced",
                tags="replaced",
                secondary_color="{replace_me}",
            ),
            got,
        )

    def test_format_invalid(self):
        to_format = self.defaults()
        to_format.name = "{invalid_placeholder}"

        self.assertRaises(
            InvalidFormatError, to_format.format, {"valid1": "", "valid2": ""}
        )
