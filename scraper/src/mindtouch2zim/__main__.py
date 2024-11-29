import sys
import tempfile

from mindtouch2zim.constants import logger
from mindtouch2zim.entrypoint import prepare_context


def main():
    try:
        with tempfile.TemporaryDirectory() as tmpdir:

            prepare_context(sys.argv[1:], tmpdir)

            # import this only once the Context has been initialized, so that it gets an
            # initialized context
            from mindtouch2zim.processor import Processor

            Processor().run()

    except SystemExit:
        logger.error("Scraper failed, exiting")
        raise
    except Exception as exc:
        logger.exception(exc)
        logger.error(f"Scraper failed with the following error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
