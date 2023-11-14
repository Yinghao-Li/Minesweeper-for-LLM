"""
# Author: Yinghao Li
# Modified: November 1st, 2023
# ---------------------------------------
# Description: Test table understanding on cell content retrieval.
"""

import os.path as osp
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
from src.game import MineField
from src.gpt import GPT, MessageCache
from src.prompts import BoardUnderstandingPrompt

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
    output_path: str = field(
        default="./output.json", metadata={"help": "where to save the dataset with sampled progress board."}
    )
    gpt_resource_path: str = field(
        default="./resources/gpt35.16k.json", metadata={"help": "path to the GPT resource file."}
    )
    n_sample_per_board: int = field(
        default=3, metadata={"help": "number of sampled progress board per original board."}
    )
    use_dict_table: bool = field(default=False, metadata={"help": "whether to use a dictionary-formatted table."})
    use_row_column_indices: bool = field(default=False, metadata={"help": "whether to use row and column indices."})
    use_examples: bool = field(default=False, metadata={"help": "whether to use examples in the prompt."})
    revise: bool = field(default=False, metadata={"help": "whether to let model revise the answer."})
    seed: int = field(default=42, metadata={"help": "Random seed."})


def main(args: Arguments):
    random.seed(args.seed)
    init_dir(osp.dirname(args.output_path), clear_original_content=False)

    gpt = GPT(resource_path=args.gpt_resource_path)

    result_list = list()

    for board_path in tqdm(glob.glob(osp.join(args.data_dir, "*"))):
        if not board_path.endswith(".json"):
            continue
        with open(board_path, "r", encoding="utf-8") as f:
            board_dict = json.load(f)

        # load the board
        m = MineField()
        m.load_board(board_path, load_action_history=True)

        # get the board at n_actions
        for action_idx in range(board_dict["n_actions"]):
            action = parse_action_str(m.action_history[action_idx])
            getattr(m, f"on_{action_type_map[action[0]]}")(*action[1:])

        for _ in range(args.n_sample_per_board):
            # randomly sample a cell coordinate to ask
            x, y = random.randint(1, m.n_rows), random.randint(1, m.n_cols)
            ground_truth = m.board_disp[x - 1, y - 1]

            # initialize the prompt
            prompt = BoardUnderstandingPrompt(
                mine_field=m,
                represent_board_as_coordinates=args.use_dict_table,
                with_row_column_ids=args.use_row_column_indices,
            )
            user_message = prompt.desc

            if args.use_examples:
                if args.use_dict_table:
                    user_message += f"\n--- EXAMPLES ---\n{prompt.navigation_dict_example1}\n--- END OF EXAMPLES ---\n"
                else:
                    user_message += f"\n--- EXAMPLES ---\n{prompt.navigation_example1}\n{prompt.navigation_example2}\n--- END OF EXAMPLES ---\n"

            if args.use_dict_table:
                user_message += f"\n--- CURRENT BOARD ---\n{m.to_dict_table()}\n\n"
            else:
                user_message += (
                    f"\n--- CURRENT BOARD ---\n{m.to_str_table(with_row_column_ids=args.use_row_column_indices)}\n\n"
                )

            user_message += f"QUESTION: What is the cell at coordinate ({x},{y})?\n"
            user_message += "ANSWER: "

            # wrap the message in MessageCache
            message_cache = MessageCache(
                system_role="You are a helpful assistant who is good at reading and understanding tables."
            )
            message_cache.add_user_message(user_message)

            response = gpt.response(message_cache)

            if args.revise:
                user_message = (
                    f"Please revise your answer and correct it if it is wrong.\nLet's think step by step.\n\nANSWER: "
                )
                message_cache.add_assistant_message(response)
                message_cache.add_user_message(user_message)
                response = gpt.response(message_cache)

            result_list.append(
                {
                    "response": response,
                    "ground_truth": ground_truth,
                }
            )

    save_json(result_list, args.output_path, collapse_level=3)


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
        (arguments,) = parser.parse_json_file(json_file=osp.abspath(sys.argv[1]))
    else:
        (arguments,) = parser.parse_args_into_dataclasses()

    if not getattr(arguments, "log_path", None):
        arguments.log_path = osp.join("./logs", f"{_current_file_name}", f"{_time}.log")

    set_logging(log_path=arguments.log_path)
    logging_args(arguments)

    main(args=arguments)
