"""
# Author: Yinghao Li
# Modified: October 26th, 2023
# ---------------------------------------
# Description: Test table understanding on cell content retrieval.
"""

import os.path as osp
import re
import json
import sys
import logging
from datetime import datetime
from dataclasses import dataclass, field

from src.argparser import ArgumentParser
from src.io import set_logging, logging_args

logger = logging.getLogger(__name__)


@dataclass
class Arguments:
    """
    Arguments regarding the training of Neural hidden Markov Model
    """

    # --- IO arguments ---
    result_path: str = field(default="./result.json", metadata={"help": "where the (to-be-)labeled dataset is saved."})


def main(args: Arguments):
    with open(args.result_path, "r", encoding="utf-8") as f:
        result_list = json.load(f)

    n_match = 0
    for result_item in result_list:
        response = result_item["response"]
        ground_truth = result_item["ground_truth"]

        response = response[:-1] if response.endswith(".") else response

        response_symbols = re.findall(r"[`'\"]([1-9.?F])[`'\"]", response)
        if len(response_symbols) == 0:
            logger.warning(f"Cannot find any symbols in response: {response}")
            logger.warning(f"Ground truth: {ground_truth}")
            logger.warning("")
            continue
        response_symbols = response_symbols[-1]
        if response_symbols == ground_truth:
            n_match += 1
        else:
            logger.warning(f"Response: {response}")
            logger.warning(f"Ground truth: {ground_truth}")
            logger.warning("")

    logger.info(f"Matched {n_match} out of {len(result_list)}.")


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
