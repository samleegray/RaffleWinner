import argparse
import logging
import sys

from raffle import Raffle, RaffleError

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a raffle from a Google Sheet")
    parser.add_argument("spreadsheet_id", help="The Google Spreadsheet ID")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Select winner without writing to sheet"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s"
    )

    try:
        raffle = Raffle(args.spreadsheet_id)
        winner = raffle.run(dry_run=args.dry_run)
        if winner:
            sys.exit(0)
        else:
            sys.exit(1)
    except RaffleError as err:
        logging.error(str(err))
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(130)
