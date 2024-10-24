import tempfile

from mindtouch2zim.entrypoint import main as entrypoint


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        entrypoint(tmpdir)


if __name__ == "__main__":
    main()
