import contextlib
import os
from pathlib import Path
from typing import Iterator, Union


@contextlib.contextmanager
def chdir(path: Union[Path, str]) -> Iterator[None]:
    """Change the current working directory."""
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)
