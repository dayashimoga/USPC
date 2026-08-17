"""Main execution entry point for python -m cloudctl."""

import sys

from cloudctl.cli import main

if __name__ == "__main__":
    sys.exit(main())
