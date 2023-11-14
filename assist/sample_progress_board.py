"""
# Author: Yinghao Li
# Modified: October 25th, 2023
# ---------------------------------------
# Description: Randomly sample progress boards from the original boards.
"""

import os.path as op
import re
import json
import sys
import logging
import glob
import random
from datetime import datetime
from dataclasses import dataclass, field
from tqdm.auto import tqdm

from src.argparser import ArgumentParser
from src.io import set_logging, logging_args, init_dir, save_json
from src.game import MineField, ActionFeedback


logger = logging.getLogger(__name__)

action_type_map = {
    "L": "left_click",
    "M": "middle_click",
    "R": "right_click",
}


@dataclass
class Arguments:
    """
    Arguments regarding the training of Neural hidden Markov Model
    """

    # --- IO arguments ---
    data_dir: str = field(default="./data/", metadata={"help": "where the (to-be-)labeled dataset is saved."})
    output_dir: str = field(
        default="./data/", metadata={"help": "where to save the dataset with sampled progress board."}
    )
    overwrite: bool = field(default=False, metadata={"help": "whether to overwrite existing boards."})
    seed: int = field(default=42, metadata={"help": "Random seed."})


def main(args: Arguments):
    random.seed(args.seed)
    init_dir(args.output_dir, clear_original_content=False)

    for board_path in tqdm(glob.glob(op.join(args.data_dir, "*"))):
        board_name = op.basename(board_path)
        output_board_path = op.join(args.output_dir, board_name)
        if op.exists(output_board_path) and not args.overwrite:
            logger.warning(f"Board {board_name} already exists in {args.output_dir}.")
            continue

        if not board_path.endswith(".json"):
            continue
        with open(board_path, "r", encoding="utf-8") as f:
            board_dict = json.load(f)
        if len(board_dict.get("action_history", list())) == 0:
            continue

        m = MineField()
        m.load_board(board_path, load_action_history=True)

        n_actions = max(1, random.randrange(len(m.action_history)))

        board_display = None
        for action_idx in range(n_actions):
            action = parse_action_str(m.action_history[action_idx])
            feedback = getattr(m, f"on_{action_type_map[action[0]]}")(*action[1:])
            if feedback != ActionFeedback.GAME_OVER:
                board_display = m.str()
            else:
                n_actions = action_idx + 1
                break

        board_dict["n_actions"] = n_actions
        board_dict["board_at_n_actions"] = board_display

        save_json(board_dict, output_board_path, collapse_level=3)


def parse_action_str(action_str: str):
    action_str = action_str.strip()
    match_result = re.search(r"([LMR]) *\(( *\d+) *, *(\d+) *\)", action_str)
    try:
        action, row_idx, col_idx = match_result.groups()
    except (AttributeError, TypeError):
        # TODO: this can be improved to provide feedback to GPT
        raise ValueError("Invalid response format.")

    return action, int(row_idx), int(col_idx)


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
