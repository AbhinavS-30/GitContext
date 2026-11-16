"""Allow python -m gitcontext alongside the installed command."""

from gitcontext.cli import main

raise SystemExit(main())
