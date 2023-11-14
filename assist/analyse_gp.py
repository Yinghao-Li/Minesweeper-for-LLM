"""
# Author: Yinghao Li
# Modified: November 4th, 2023
# ---------------------------------------
# Description: Test table understanding on cell content retrieval.
"""

import os.path as osp
import re
import json
import sys
import logging
import glob
from datetime import datetime
from tqdm.auto import tqdm
from dataclasses import dataclass, field

from src.argparser import ArgumentParser
from src.io import set_logging, logging_args
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
    result_dir: str = field(
        default="./output/board-solve", metadata={"help": "where the experiment results are saved."}
    )


def main(args: Arguments):
    n_actions = 0
    n_valid_actions = 0
    n_win = 0
    n_game_over = 0
    n_repeat = 0
    n_boards = 0
    n_flagged_mines = 0
    valid_actions = list()

    for result_path in tqdm(glob.glob(osp.join(args.result_dir, "*.json"))):
        file_name = osp.basename(result_path)
        data_path = osp.join(args.data_dir, file_name)
        with open(result_path, "r", encoding="utf-8") as f:
            result_dict = json.load(f)
        conversation = result_dict["conversation"]
        with open(result_path.replace(".json", ".txt"), "w", encoding="utf-8") as f:
            f.write(conversation)

        action_history = result_dict["action_history"]
        m = MineField(strict_winning_condition=True).load_board(data_path)

        for idx, action in enumerate(action_history):
            parsed_action = parse_action_str(action)
            feedback = getattr(m, f"on_{action_type_map[parsed_action[0]]}")(*parsed_action[1:])

            if idx == 0:
                continue

            if feedback in (ActionFeedback.SUCCESS, ActionFeedback.GAME_WIN, ActionFeedback.GAME_OVER):
                valid_actions.append(action)
                n_valid_actions += 1
            if feedback == ActionFeedback.GAME_WIN:
                n_win += 1
                logger.info(f"Board {file_name} solved!")
            if feedback == ActionFeedback.GAME_OVER:
                n_game_over += 1

        n_actions += len(action_history) - 1
        n_repeat += len(action_history) - len(set(action_history))
        n_boards += 1
        n_flagged_mines += m.n_correctly_flagged_mines

    logger.info(f"Total number of actions: {n_actions}")
    logger.info(f"Total number of valid actions: {n_valid_actions}, ratio: {n_valid_actions / n_actions:.3f}")
    logger.info(f"Total number of repeated actions: {n_repeat}, ratio: {n_repeat / n_actions:.3f}")
    logger.info(f"Total number of wins: {n_win}, ratio: {n_win / n_boards:.3f}")
    logger.info(f"Total number of game overs: {n_game_over}, ratio: {n_game_over / n_boards:.3f}")
    logger.info(f"Total number of boards: {n_boards}")
    logger.info(
        f"Total number of flagged mines: {n_flagged_mines}, ratio: {n_flagged_mines / (n_boards*m.n_mines):.3f}"
    )
    valid_action_str = "\n".join(valid_actions)
    # logger.info(f"Valid actions: \n{valid_action_str}")

    return None


def parse_action_str(action_str: str) -> str:
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
    _current_file_name = osp.basename(__file__)
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
        arguments.log_path = osp.join("./logs", f"{_current_file_name}", f"{_time}.log")

    set_logging(log_path=arguments.log_path)
    logging_args(arguments)

    main(args=arguments)
