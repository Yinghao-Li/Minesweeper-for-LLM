"""
# Author: Yinghao Li
# Modified: October 14th, 2023
# ---------------------------------------
# Description: Generate Minesweeper boards for future use.
"""

import os.path as op
import sys
import logging
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from tqdm.auto import tqdm

from src.argparser import ArgumentParser
from src.io import set_logging, logging_args, init_dir
from src.game import MineField

logger = logging.getLogger(__name__)


@dataclass
class Arguments:
    """
    Arguments regarding the training of Neural hidden Markov Model
    """

    # --- IO arguments ---
    n_rows: int = field(default=9, metadata={"help": "Number of rows in the board."})
    n_cols: int = field(default=9, metadata={"help": "Number of columns in the board."})
    n_mines: int = field(default=10, metadata={"help": "Number of mines in the board."})
    n_board: int = field(default=1000, metadata={"help": "Number of boards to generate."})
    output_dir: str = field(default="./data/", metadata={"help": "where to save constructed dataset."})
    log_path: str = field(default=None, metadata={"help": "Path to save the log file."})
    overwrite_output: bool = field(default=False, metadata={"help": "Whether overwrite existing outputs."})

    def __post_init__(self):
        self.output_dir = op.join(self.output_dir, f"{self.n_rows}x{self.n_cols}-{self.n_mines}")


def main(args: Arguments):
    init_dir(args.output_dir, clear_original_content=args.overwrite_output)
    init_dir(op.join(args.output_dir, "01-10"), clear_original_content=args.overwrite_output)
    init_dir(op.join(args.output_dir, "10-20"), clear_original_content=args.overwrite_output)
    init_dir(op.join(args.output_dir, "20-30"), clear_original_content=args.overwrite_output)
    init_dir(op.join(args.output_dir, "30-40"), clear_original_content=args.overwrite_output)
    init_dir(op.join(args.output_dir, "40-inf"), clear_original_content=args.overwrite_output)

    board_cache = np.array([], dtype=bool).reshape(0, args.n_rows, args.n_cols)

    for seed in tqdm(range(args.n_board)):
        m = MineField(args.n_rows, args.n_cols, args.n_mines, seed=seed)
        m.on_left_click(int(np.ceil(args.n_rows / 2)), int(np.ceil(args.n_cols / 2)))

        if np.any(np.all(m.board_mine == board_cache, axis=(1, 2))):
            continue
        board_cache = np.vstack([board_cache, np.expand_dims(m.board_mine, axis=0)])

        if m.n_revealed_cells >= 40:
            sub_dir = "40-inf"
        elif m.n_revealed_cells >= 30:
            sub_dir = "30-40"
        elif m.n_revealed_cells >= 20:
            sub_dir = "20-30"
        elif m.n_revealed_cells >= 10:
            sub_dir = "10-20"
        else:
            sub_dir = "01-10"

        m.save_board(op.join(args.output_dir, sub_dir, f"{seed:03d}.json"), additional_addribute="n_revealed_cells")

    logger.info("Done.")
    return None


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
