import os.path as osp
import sys
import logging
import glob
from tqdm.auto import tqdm
from datetime import datetime

from src.argparser import ArgumentParser
from src.args import Arguments, Config
from src.io import set_logging, init_dir, save_json
from src.interaction import Interaction
from src.game import ActionFeedback

logger = logging.getLogger(__name__)


def main(args: Arguments):
    config = Config().from_args(args).log()
    if osp.isdir(config.board_path_or_dir):
        board_paths = glob.glob(osp.join(config.board_path_or_dir, "*.json"))
    else:
        board_paths = [config.board_path_or_dir]

    for board_path in tqdm(board_paths):
        output_path = osp.join(config.output_dir, f"{osp.basename(board_path)}")

        if osp.exists(output_path):
            logger.warning(f"Output file {output_path} already exists! Skipping...")
            continue

        interaction = Interaction(board_path=board_path, **config.as_dict())
        responses = list()
        for _ in range(config.max_steps):
            try:
                response = interaction.step()
                responses.append(response)
            except ValueError:
                logger.error("Exiting due to invalid response format!")
                break

            if interaction.action_feedback in (ActionFeedback.GAME_WIN, ActionFeedback.GAME_OVER):
                break

        output_dict = {
            "conversation": str(interaction.messages),
            "action_history": interaction.action_history,
            "responses": responses,
        }
        init_dir(config.output_dir, clear_original_content=False)
        save_json(output_dict, output_path, collapse_level=3)

        with open(output_path.replace(".json", ".txt"), "w", encoding="utf-8") as f:
            f.write(str(interaction.messages))


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
    main(arguments)
