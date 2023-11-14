"""
# Author: Yinghao Li
# Modified: November 11th, 2023
# ---------------------------------------
# Description: Generate Minesweeper boards for future use.
"""

import os.path as op
import json
import sys
import logging
import glob
from datetime import datetime
from dataclasses import dataclass, field
from tqdm.auto import tqdm

from src.argparser import ArgumentParser
from src.io import set_logging, logging_args
from src.game import MineField

import sys
import logging
from src.game import MineField, MinesweeperGUI
from src.io import set_logging, logging_args
from PyQt6.QtWidgets import QApplication


logger = logging.getLogger(__name__)


@dataclass
class Arguments:
    """
    Arguments regarding the training of Neural hidden Markov Model
    """

    # --- IO arguments ---
    data_dir_or_path: str = field(default="./data", metadata={"help": "where the (to-be-)labeled dataset is saved."})
    no_saving: bool = field(default=False, metadata={"help": "whether to save the labels."})


def main(args: Arguments):
    app = QApplication(list())

    if op.isfile(args.data_dir_or_path):
        data_paths = [args.data_dir_or_path]
    elif op.isdir(args.data_dir_or_path):
        data_paths = glob.glob(op.join(args.data_dir_or_path, "*.json"))
    else:
        raise ValueError(f"Invalid data dir or path: {args.data_dir_or_path}")

    for board_path in tqdm(data_paths):
        if not board_path.endswith(".json"):
            continue
        with open(board_path, "r", encoding="utf-8") as f:
            board_dict = json.load(f)
        if board_dict.get("labeled", False) and len(board_dict.get("action_history", list())) != 0:
            continue

        m = MineField()
        m.load_board(board_path)

        window = MinesweeperGUI(m)
        window.show()
        app.exec()
        if not args.no_saving:
            m.save_board(
                board_path,
                additional_addribute="action_history",
                n_revealed_cells=board_dict["n_revealed_cells"],
                labeled=True,
            )

        app.quit()


if __name__ == "__main__":
    _time = datetime.now().strftime("%m.%d.%y-%H.%M")
    _current_file_name = op.basename(__file__)
    if _current_file_name.endswith(".py"):
        _current_file_name = _current_file_name[:-3]

    # --- set up arguments ---
    parser = ArgumentParser(Arguments)
    if len(sys.argv) == 2 and sys.argv[1].endswith(".json"):
        # If we pass only one argument to the script, and it's the path to a json file,
        # let's parse it to get our arguments.
        (arguments,) = parser.parse_json_file(json_file=op.abspath(sys.argv[1]))
    else:
        (arguments,) = parser.parse_args_into_dataclasses()

    if not getattr(arguments, "log_path", None):
        arguments.log_path = op.join("./logs", f"{_current_file_name}", f"{_time}.log")

    set_logging(log_path=arguments.log_path)
    logging_args(arguments)

    main(args=arguments)
