"""
# Author: Yinghao Li
# Modified: November 11th, 2023
# ---------------------------------------
# Description: Test table understanding on cell content retrieval.
"""

import re
import json
import sys
import logging
import glob
import numpy as np
import os.path as osp
from datetime import datetime
from tqdm.auto import tqdm
from dataclasses import dataclass, field

from src.argparser import ArgumentParser
from src.io import set_logging, logging_args, init_dir
from src.game import MineField, ActionFeedback

logger = logging.getLogger(__name__)

action_type_map = {
    "L": "left_click",
    "M": "middle_click",
    "R": "right_click",
}
n_rows = 5
n_cols = 5
unchecked_cell = "?"
number_cells = ",".join([f"`{i}'" for i in range(1, 8)])
flag_cell = "F"
game_feedback_to_prompt = {
    ActionFeedback.SUCCESS: "Action successful!",
    ActionFeedback.GAME_WIN: "Congratulations, you've won the game!",
    ActionFeedback.GAME_OVER: "Game over. Better luck next time!",
    ActionFeedback.UNEXIST_CELL: f"Invalid Coordinates! Please make sure your coordinate are within [1, {n_rows}] for rows and [1, {n_cols}] for columns.",
    ActionFeedback.LEFT_CLICK_EMPTY_CELL: f"Invalid action: Cannot left-click a blank cell. Left-click is only for unopened cells (`{unchecked_cell}').",
    ActionFeedback.LEFT_CLICK_FLAG_CELL: f"Invalid action: Cannot left-click a flagged cell. Left-click is only for unopened cells (`{unchecked_cell}').",
    ActionFeedback.LEFT_CLICK_NUMBER_CELL: f"Invalid action: Cannot left-click a numbered cell. Left-click is only for unopened cells (`{unchecked_cell}').",
    ActionFeedback.MIDDLE_CLICK_EMPTY_CELL: f"Invalid action: Cannot middle-click a blank cell. Middle-click is only for numbered cells (`{number_cells}').",
    ActionFeedback.MIDDLE_CLICK_FLAG_CELL: f"Invalid action: Cannot middle-click a flagged cell. Middle-click is only for numbered cells (`{number_cells}').",
    ActionFeedback.MIDDLE_CLICK_UNCHECKED_CELL: f"Invalid action: Cannot middle-click an unopened cell. Middle-click is only for numbered cells (`{number_cells}').",
    ActionFeedback.RIGHT_CLICK_EMPTY_CELL: f"Invalid action: Cannot right-click a blank cell. Right-click is only for unopened (`{unchecked_cell}') or flagged cells (`{flag_cell}').",
    ActionFeedback.RIGHT_CLICK_NUMBER_CELL: f"Invalid action: Cannot right-click a numbered cell. Right-click is only for unopened (`{unchecked_cell}') or flagged cells (`{flag_cell}').",
    ActionFeedback.MIDDLE_CLICK_NUMBER_CELL_NO_FLAG: f"Error: No flagged cells detected nearby. Flag adjacent mines before middle-clicking.",
    ActionFeedback.MIDDLE_CLICK_NUMBER_CELL_NUMBER_MISMATCH: f"Error: Flag count mismatch. Ensure all adjacent mines are flagged before middle-clicking.",
    ActionFeedback.START_BY_MIDDLE_CLICK: f"Please begin by left-clicking on a cell.",
    ActionFeedback.START_BY_RIGHT_CLICK: f"Please begin by left-clicking on a cell.",
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
    tgt_dir: str = field(default="./output/reasoning", metadata={"help": "where organized results are saved."})


def main(args: Arguments):
    selected_boards = list()
    n_valid_actions_list = list()

    result_paths = glob.glob(osp.join(args.result_dir, "*.json"))
    for result_path in tqdm(result_paths):
        with open(result_path, "r", encoding="utf-8") as f:
            result_dict = json.load(f)

        file_name = osp.basename(result_path)
        data_path = osp.join(args.data_dir, file_name)

        action_history = result_dict["action_history"]
        m = MineField(strict_winning_condition=True).load_board(data_path)

        n_valid_actions = 0
        for idx, action in enumerate(action_history):
            parsed_action = parse_action_str(action)
            feedback = getattr(m, f"on_{action_type_map[parsed_action[0]]}")(*parsed_action[1:])

            if idx == 0:
                continue
            if feedback in (ActionFeedback.SUCCESS, ActionFeedback.GAME_WIN, ActionFeedback.GAME_OVER):
                n_valid_actions += 1
            if feedback == ActionFeedback.GAME_WIN:
                selected_boards.append(result_path)

        n_valid_actions_list.append(n_valid_actions)

    selected_boars_ids = np.argsort(n_valid_actions_list)[-5 + len(selected_boards) :]
    selected_boards.extend([result_paths[idx] for idx in selected_boars_ids])

    init_dir(args.tgt_dir, False)

    feedback = None
    n_valid_actions = 0
    total_actions = 0
    for result_path in selected_boards:
        with open(result_path, "r", encoding="utf-8") as f:
            result_dict = json.load(f)

        file_name = osp.basename(result_path)
        data_path = osp.join(args.data_dir, file_name)
        output_path = osp.join(args.tgt_dir, file_name.replace(".json", ".txt"))
        if osp.exists(output_path):
            continue
        m = MineField(strict_winning_condition=True).load_board(data_path)

        actions = result_dict["action_history"]
        if "responses" in result_dict:
            responses = result_dict["responses"]
        else:
            responses = re.findall(r">> ASSISTANT:(.*?)>> USER", result_dict["conversation"], re.DOTALL)

        conv = ""
        for idx, (action, response) in enumerate(zip(actions, responses)):
            if idx > 0:
                conv += ">> USER:\n"
                conv += feedback_to_prompt(actions[idx - 1], feedback)
                conv += f"--- CURRENT BOARD ---\n```\n{m.to_str_table()}\n```\n\n"

            parsed_action = parse_action_str(action)
            feedback = getattr(m, f"on_{action_type_map[parsed_action[0]]}")(*parsed_action[1:])

            if idx == 0:
                continue

            if feedback in (ActionFeedback.SUCCESS, ActionFeedback.GAME_WIN, ActionFeedback.GAME_OVER):
                n_valid_actions += 1

            conv += ">> ASSISTANT:"
            conv += f"\n{response.strip()}\n\n"

            total_actions += 1

        with open(osp.join(args.tgt_dir, file_name.replace(".json", ".txt")), "w", encoding="utf-8") as f:
            f.write(conv)

    logger.info(f"Total number of actions: {total_actions}")
    logger.info(f"Total number of valid actions: {n_valid_actions}, ratio: {n_valid_actions / total_actions:.3f}")

    return None


def parse_action_str(action_str: str) -> tuple[str, int, int]:
    action_str = action_str.strip()
    match_result = re.search(r"([LMR]) *\(( *\d+) *, *(\d+) *\)", action_str)
    try:
        action, row_idx, col_idx = match_result.groups()
    except (AttributeError, TypeError):
        # TODO: this can be improved to provide feedback to GPT
        raise ValueError("Invalid response format.")

    return action, int(row_idx), int(col_idx)


def feedback_to_prompt(action, feedback) -> str:
    if feedback == ActionFeedback.SUCCESS:
        return ""
    feedback_str = f'Your previous action "{action}" is invalid. Error Message:\n'
    feedback_str += game_feedback_to_prompt[feedback]
    feedback_str += "\nPlease follow the instructions and try again.\n\n"
    return feedback_str


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
        (arguments,) = parser.parse_json_file(json_file=osp.abspath(sys.argv[1]))
    else:
        (arguments,) = parser.parse_args_into_dataclasses()

    if not getattr(arguments, "log_path", None):
        arguments.log_path = osp.join("./logs", f"{_current_file_name}", f"{_time}.log")

    set_logging(log_path=arguments.log_path)
    logging_args(arguments)

    main(args=arguments)
