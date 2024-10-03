import argparse

from libretexts2zim.entrypoint import add_zim_config_flags, zim_defaults
from libretexts2zim.processor import ZimConfig


def test_zim_defaults_validity():
    parser = argparse.ArgumentParser()
    add_zim_config_flags(parser, zim_defaults())

    # Assert parsing the defaults doesn't raise an error.
    ZimConfig.of(parser.parse_args(["--library-name", "library-name"]))
