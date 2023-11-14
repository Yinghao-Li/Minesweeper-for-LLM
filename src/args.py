"""
# Author: Yinghao Li
# Modified: November 3rd, 2023
# ---------------------------------------
# Description: Base classes for arguments and configurations.
"""

import os.path as osp
import json
import glob
import logging
from typing import Optional
from dataclasses import dataclass, field, asdict
from .io import prettify_json


logger = logging.getLogger(__name__)

__all__ = ["Arguments", "Config"]


@dataclass
class Arguments:
    """
    Arguments regarding the training of Neural hidden Markov Model
    """

    empty_cell: str = field(default=".", metadata={"help": "Empty cell symbol"})
    mine_cell: str = field(default="*", metadata={"help": "Mine cell symbol"})
    flag_cell: str = field(default="F", metadata={"help": "Flag cell symbol"})
    unchecked_cell: str = field(default="?", metadata={"help": "Unchecked cell symbol"})

    n_rows: int = field(default=9, metadata={"help": "Number of rows"})
    n_cols: int = field(default=9, metadata={"help": "Number of columns"})
    n_mines: int = field(default=10, metadata={"help": "Number of mines"})
    seed: int = field(default=42, metadata={"help": "Random seed"})
    max_steps: int = field(default=100, metadata={"help": "Maximum number of steps"})

    gpt_resource_path: str = field(default="./resources/gpt35.16k.json", metadata={"help": "Path to GPT resources"})
    board_path_or_dir: str = field(default=None, metadata={"help": "Path to board file"})

    strict_winning_condition: bool = field(default=False, metadata={"help": "Whether to use strict winning condition"})
    use_row_column_indices: bool = field(default=False, metadata={"help": "whether to use row and column indices."})
    use_compressed_history: bool = field(default=False, metadata={"help": "whether to use compressed history."})
    represent_board_as_coordinate: bool = field(
        default=False, metadata={"help": "whether to represent board as coordinate."}
    )

    output_dir: str = field(default="./output/board-solve/", metadata={"help": "Output directory"})


@dataclass
class Config(Arguments):
    # --- Properties and Functions ---
    def __getitem__(self, item):
        if isinstance(item, str):
            return getattr(self, item)
        else:
            raise ValueError("`Config` can only be subscribed by str!")

    def as_dict(self):
        return asdict(self)

    def from_args(self, args):
        """
        Initialize configuration from arguments

        Parameters
        ----------
        args: arguments (parent class)

        Returns
        -------
        self (type: BertConfig)
        """
        arg_elements = {
            attr: getattr(args, attr)
            for attr in dir(args)
            if not callable(getattr(args, attr)) and not attr.startswith("__") and not attr.startswith("_")
        }
        for attr, value in arg_elements.items():
            try:
                setattr(self, attr, value)
            except AttributeError:
                pass

        self.check()

        return self

    def check(self):
        if self.board_path_or_dir is None:
            return self

        if osp.isdir(self.board_path_or_dir):
            board_paths = glob.glob(osp.join(self.board_path_or_dir, "*.json"))
            assert len(board_paths) > 0, FileNotFoundError(f"No board file found in {self.board_path_or_dir}!")
        else:
            board_paths = [self.board_path_or_dir]

        with open(board_paths[0], "r", encoding="utf-8") as f:
            board_dict = json.load(f)
            self.n_rows = board_dict["n_rows"]
            self.n_cols = board_dict["n_cols"]
            self.n_mines = board_dict["n_mines"]

        for board_path in board_paths[1:]:
            with open(board_path, "r", encoding="utf-8") as f:
                board_dict = json.load(f)

            assert (
                self.n_rows == board_dict["n_rows"]
                and self.n_cols == board_dict["n_cols"]
                and self.n_mines == board_dict["n_mines"]
            ), ValueError(f"Board size mismatch! ")

        return self

    def save(self, file_dir: str, file_name: Optional[str] = "config"):
        """
        Save configuration to file

        Parameters
        ----------
        file_dir: file directory
        file_name: file name (suffix free)

        Returns
        -------
        self
        """
        if osp.isdir(file_dir):
            file_path = osp.join(file_dir, f"{file_name}.json")
        elif osp.isdir(osp.split(file_dir)[0]):
            file_path = file_dir
        else:
            raise FileNotFoundError(f"{file_dir} does not exist!")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.exception(f"Cannot save config file to {file_path}; " f"encountered Error {e}")
            raise e
        return self

    def load(self, file_dir: str, file_name: Optional[str] = "config"):
        """
        Load configuration from stored file

        Parameters
        ----------
        file_dir: file directory
        file_name: file name (suffix free)

        Returns
        -------
        self
        """
        if osp.isdir(file_dir):
            file_path = osp.join(file_dir, f"{file_name}.json")
            assert osp.isfile(file_path), FileNotFoundError(f"{file_path} does not exist!")
        elif osp.isfile(file_dir):
            file_path = file_dir
        else:
            raise FileNotFoundError(f"{file_dir} does not exist!")

        logger.info(f"Setting {type(self)} parameters from {file_path}.")

        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        for attr, value in config.items():
            try:
                setattr(self, attr, value)
            except AttributeError:
                pass
        return self

    def log(self):
        """
        Log all configurations
        """
        elements = {
            attr: getattr(self, attr)
            for attr in dir(self)
            if not callable(getattr(self, attr)) and not (attr.startswith("__") or attr.startswith("_"))
        }
        logger.info(f"Configurations:\n{prettify_json(json.dumps(elements, indent=2), collapse_level=2)}")

        return self
