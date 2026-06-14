"""Dev launcher: `uv run src/main.py`. The real logic and the `pip-robot`
console script both live in modules.cli (running this file puts src/ on sys.path)."""
from modules.cli import main

if __name__ == "__main__":
    main()
