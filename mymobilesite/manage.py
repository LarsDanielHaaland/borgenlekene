#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Updated to use the new `project` package to reduce ambiguity between
    # the repository root and the inner package. The old value is left here
    # in a comment for reference.
    # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mymobilesite.settings")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
