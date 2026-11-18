import argparse
from pathlib import Path

from records.schema import initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description='Initialize or reopen the inspection database schema.')
    parser.add_argument('database', type=Path)
    args = parser.parse_args()
    initialize_database(args.database)
    print(f'Inspection database ready: {args.database}')


if __name__ == '__main__':
    main()
