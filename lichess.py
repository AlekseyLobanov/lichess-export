#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import shutil
import time
import tempfile
import logging


import grequests
import requests


__author__ = "Aleksey Lobanov"
__license__ = "MIT"
__email__ = "i@likemath.ru"

SLEEP_STATUS_CODE = 429
SLEEP_TIME = 60
REQUESTS_NEED_VERIFY = False


def getTempfileName(ext=""):
    """Returns full path to temp file with with `ext` extension"""

    return os.path.join(
        tempfile.gettempdir(),
        sys.argv[0] + next(tempfile._get_candidate_names()) + ext
    )


def getGamesListUrl(user_name, page, block_size=100):
    """Returns lichess url for downloading list of games"""

    URL_TEMPLATE = "https://en.lichess.org/api/user/{}/games?page={}&nb={}"
    return URL_TEMPLATE.format(user_name, page, block_size)


def getGamePgnUrl(game_id):
    """Returns lichess url for game with `game_id` id"""

    URL_TEMPLATE = "https://en.lichess.org/game/export/{}.pgn"
    return URL_TEMPLATE.format(game_id)


def getGamesList(user_name):
    """
    Returns generator that returns chunks with id:
    ["game1","game2",..], next chunk
    """
    global SLEEP_STATUS_CODE

    games_count = 0
    cur_page_ind = 1

    while True:
        r = requests.get(getGamesListUrl(user_name, cur_page_ind))
        if r.status_code == SLEEP_STATUS_CODE:
            logging.debug("Sleeping by status code")
            time.sleep(SLEEP_TIME)
            continue
        elif r.status_code == 200:
            logging.info("New page {} with game identifiers".format(
                cur_page_ind
            ))
            r_json = r.json()
            cur_ids = [game['id'] for game in r_json["currentPageResults"]]
            games_count += len(cur_ids)
            yield tuple(cur_ids)

            if r_json['nextPage'] is None:
                logging.debug("Last page")
                break
            else:
                cur_page_ind += 1
    logging.info("Downloaded {} game identifiers".format(
        games_count
    ))


def downloadGamesToFile(game_ids, file_name, thread_count):
    """
    Creates big pool of async pgn downloads.
    It is assumed that loading png is always successful (no 429 errors).
    All pgns saved to one file
    game_ids is chunk generator
    """

    with open(file_name, "wb") as file_pgn:
        # imap returns generator
        for chunk in game_ids:
            reqs = [grequests.get(getGamePgnUrl(game_id), verify=REQUESTS_NEED_VERIFY) for game_id in chunk]
            for req in grequests.imap(reqs, size=thread_count):
                try:
                    logging.info("Downloaded {}".format(req.url))
                    file_pgn.write((req.text + "\n\n").encode("utf-8"))
                finally:
                    for req_prev in req.history:
                        req_prev.release_conn()
                    req.raw.release_conn()


def writePgn(user_name, file_name, thread_count):
    """Write pgn for selected usern to file"""

    downloadGamesToFile(getGamesList(user_name), file_name, thread_count)


def createScidFromPgn(pgn_name, scid_name, is_save_pgn=False):
    logging.debug("Saving to scid base: {}".format(scid_name))
    if (os.path.isfile(scid_name + ".si4") or
            os.path.isfile(scid_name + ".sg4") or
            os.path.isfile(scid_name + ".sn4")):
        logging.warning("Scid base already exists!")
        sys.exit(1)

    logging.debug("Executing: " + 'pgnscid -f "{}" "{}"'.format(
        pgn_name, scid_name
    ))
    os.system('pgnscid -f "{}" "{}"'.format(pgn_name, scid_name))

    if not is_save_pgn:
        logging.debug("Removing old file: {}".format(pgn_name))
        os.remove(pgn_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tool for export your games to Scid or PGN"
    )
    parser.add_argument("-n", "--name", help='Your lichess id', required=True)
    parser.add_argument(
        "-t", "--type", nargs='?', choices=['pgn', 'scid'],
        help='Output type', default='scid', const='scid'
    )
    parser.add_argument(
        "--threads", help='Number of threads for PGN downloading',
        default=4, type=int
    )
    parser.add_argument("-o", "--output", help='Output filename', required=True)
    parser.add_argument(
        "--logging", nargs='?', choices=['off', 'info', 'debug'],
        help='Verbosity of logging', default='info', const='info'
    )
    args = parser.parse_args()

    LOGGING_SELECTOR = {
        "off": logging.ERROR,
        "info": logging.INFO,
        "debug": logging.DEBUG
    }
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=LOGGING_SELECTOR[args.logging],
        datefmt="%H:%M:%S"
    )
    args.name = args.name.lower()

    logging.debug(("Arguments: name - {}, type - {}," +
                  "threads - {}, out - {}, logging - {}").format(
        args.name, args.type, args.threads, args.output, args.logging
    ))

    temp_pgn_filename = getTempfileName('.pgn')
    logging.debug("Temp pgn filename: {}".format(temp_pgn_filename))
    writePgn(args.name, temp_pgn_filename, args.threads)

    if args.type == 'pgn':
        if args.output.lower().split('.')[-1] != 'pgn':
            args.output += '.pgn'
        shutil.move(temp_pgn_filename, args.output)
    elif args.type == 'scid':
        createScidFromPgn(temp_pgn_filename, args.output)
    else:
        logging.error("Wrong type of file after argparse checking")
        sys.exit(1)
