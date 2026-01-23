import argparse
import logging

from raffle import Raffle

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="Run a raffle from a Google Sheet")
    parser.add_argument("spreadsheet_id", help="The Google Spreadsheet ID")
    args = parser.parse_args()

    raffle = Raffle(args.spreadsheet_id)
    raffle.run()
