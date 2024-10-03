# Libretexts.org scraper

This scraper downloads [libretexts.org](https://libretexts.org/) courses and puts them in ZIM files,
a clean and user friendly format for storing content for offline usage.

[![CodeFactor](https://www.codefactor.io/repository/github/openzim/libretexts/badge)](https://www.codefactor.io/repository/github/openzim/libretexts)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![codecov](https://codecov.io/gh/openzim/libretexts/branch/main/graph/badge.svg)](https://codecov.io/gh/openzim/libretexts)
[![PyPI version shields.io](https://img.shields.io/pypi/v/libretexts2zim.svg)](https://pypi.org/project/libretexts2zim/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/libretexts2zim.svg)](https://pypi.org/project/libretexts2zim)

## Installation

There are three main ways to install and use `libretexts2zim` from most recommended to least:

<details>
<summary>Install using a pre-built container</summary>

1. Download the image using `docker`:

   ```sh
   docker pull ghcr.io/openzim/libretexts
   ```

</details>
<details>
<summary>Build your own container</summary>

1. Clone the repository locally:

   ```sh
   git clone https://github.com/openzim/libretexts.git && cd libretexts
   ```

1. Build the image:

   ```sh
   docker build -t ghcr.io/openzim/libretexts .
   ```

</details>
<details>
<summary>Run the software locally using Hatch</summary>

1. Clone the repository locally:

   ```sh
   git clone https://github.com/openzim/libretexts.git && cd libretexts
   ```

1. Install [Hatch](https://hatch.pypa.io/):

   ```sh
   pip3 install hatch
   ```

1. Start a hatch shell to install software and dependencies in an isolated virtual environment.

   ```sh
   hatch shell
   ```

1. Run the `libretexts2zim` command:

   ```sh
   libretexts2zim --help
   ```

</details>

## Usage

> [!WARNING]
> This project is still a work in progress and isn't ready for use yet, the commands below are examples only.

```sh
# Get help
docker run -v output:/output ghcr.io/openzim/libretexts libretexts2zim --help
```

```sh
# Create a ZIM for https://geo.libretexts.org
docker run -v output:/output ghcr.io/openzim/libretexts libretexts2zim --library-slug geo --library-name Geosciences
```

## Developing

Use the commands below to set up the project once:

```sh
# Install hatch if it isn't installed already.
❯ pip install hatch

# Local install (in default env) / re-sync packages
❯ hatch run pip list

# Set-up pre-commit
❯ pre-commit install
```

The following commands can be used to build and test the scraper:

```sh
# Show scripts
❯ hatch env show

# linting, testing, coverage, checking
❯ hatch run lint:all
❯ hatch run lint:fixall

# run tests on all matrixed' envs
❯ hatch run test:run

# run tests in a single matrixed' env
❯ hatch env run -e test -i py=3.12 coverage

# run static type checks
❯ hatch env run check:all

# building packages
❯ hatch build
```

### Contributing

This project adheres to openZIM's [Contribution Guidelines](https://github.com/openzim/overview/wiki/Contributing).

This project has implemented openZIM's [Python bootstrap, conventions and policies](https://github.com/openzim/_python-bootstrap/blob/main/docs/Policy.md) **v1.0.3**.

See details for contributions in [CONTRIBUTING.md](CONTRIBUTING.md).
