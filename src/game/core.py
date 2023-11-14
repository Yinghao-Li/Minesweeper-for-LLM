"""
# Author: Yinghao Li
# Modified: November 3rd, 2023
# ---------------------------------------
# Description: Implement the minesweeper game.
# Reference: https://github.com/pyGuru123/Python-Games/tree/master/MineSweeper
"""

import re
import json
import copy
import numpy as np
import logging
from itertools import product
from enum import Enum
from typing import Union

from src.io import save_json

logger = logging.getLogger(__name__)

whitespace_start_end = re.compile(r"^[ \t]+|[ \t]+$", re.MULTILINE)
tailing_comma = re.compile(r",$", re.MULTILINE)


def replace_idx_quotes(s):
    lines = s.split("\n")
    lines[0] = re.sub(r"[`']", r'"', lines[0])
    for idx, line in enumerate(lines[1:], start=1):
        lines[idx] = re.sub(r"[`'](\d+)'", r'"\g<1>"', line, count=1)
    return "\n".join(lines)


class ActionFeedback(Enum):
    SUCCESS = 0
    UNEXIST_CELL = 1
    MIDDLE_CLICK_UNCHECKED_CELL = 2
    MIDDLE_CLICK_FLAG_CELL = 3
    MIDDLE_CLICK_EMPTY_CELL = 4
    RIGHT_CLICK_NUMBER_CELL = 5
    RIGHT_CLICK_EMPTY_CELL = 6
    LEFT_CLICK_NUMBER_CELL = 7
    LEFT_CLICK_EMPTY_CELL = 8
    LEFT_CLICK_FLAG_CELL = 9
    GAME_OVER = 10
    GAME_WIN = 11
    MIDDLE_CLICK_NUMBER_CELL_NO_FLAG = 12
    MIDDLE_CLICK_NUMBER_CELL_NUMBER_MISMATCH = 13
    START_BY_RIGHT_CLICK = 14
    START_BY_MIDDLE_CLICK = 15


class MineField:
    """
    Class to implement the minesweeper game.
    """

    def __init__(
        self,
        n_rows=9,
        n_cols=9,
        n_mines=10,
        seed=42,
        display_on_action=False,
        empty_cell=".",
        mine_cell="*",
        flag_cell="F",
        unchecked_cell="?",
        strict_winning_condition=False,
    ):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n_mines = n_mines
        self.display_on_action = display_on_action
        self.strict_winning_condition = strict_winning_condition

        self.board_true = None
        self.board_disp = None
        self.board_mine = None
        self.board_disp_with_index = None
        self.board_disp_prev = None

        self.empty_cell = empty_cell
        self.mine_cell = mine_cell
        self.flag_cell = flag_cell
        self.unchecked_cell = unchecked_cell

        self.first_move = True
        self.game_over = False
        self.action_history = list()

        self.seed = seed
        self.init_disp_board()

    def place_mines(self, num: int = None, exclude: tuple[int, int] = None):
        if num is None:
            num = self.n_mines

        assert num <= self.n_rows * self.n_cols

        np.random.seed(self.seed)
        board_rand = np.random.rand(self.n_rows, self.n_cols)

        board_rand_flat_sorted = np.sort(board_rand.flatten())
        threshold = board_rand_flat_sorted[num - 1]

        board_bool = board_rand <= threshold

        if exclude and board_bool[exclude]:
            threshold = board_rand_flat_sorted[num]
            board_bool = board_rand <= threshold
            board_bool[exclude] = False

        self.board_mine = board_bool

        return self

    def init_disp_board(self):
        self.board_disp = np.empty((self.n_rows, self.n_cols), dtype=str)
        self.board_disp.fill(self.unchecked_cell)
        return self

    def infer_board(self):
        self.board_true = np.empty((self.n_rows, self.n_cols), dtype=str)
        for i, j in product(range(self.n_rows), range(self.n_cols)):
            self.board_true[i, j] = str(self.count_mines(i, j))
        self.board_true[self.board_mine] = self.mine_cell
        self.board_true[self.board_true == "0"] = self.empty_cell

    def on_first_move(self, x, y):
        if self.board_mine is None:
            self.place_mines(exclude=(x, y))

        self.infer_board()
        self.init_disp_board()
        self.add_index()

        if self.board_true[x, y] == self.mine_cell:
            return self.on_game_over()

        self.board_disp_prev = copy.deepcopy(self.board_disp)
        # self.board_disp[x, y] = self.board_true[x, y]
        self.update_adjacent_cells(x, y)
        self.first_move = False

        if self.display_on_action:
            self.display()

        if self.check_game_win():
            return ActionFeedback.GAME_WIN

        return ActionFeedback.SUCCESS

    def on_left_click(self, x: int, y: int):
        """
        Left click event handler.
        """
        self.action_history.append(f"L({x},{y})")
        x -= 1
        y -= 1

        if not self.is_valid_cell(x, y):
            return ActionFeedback.UNEXIST_CELL

        if self.game_over:
            return self.on_game_over()

        if self.first_move:
            return self.on_first_move(x, y)

        # invalid operations
        if self.board_disp[x, y] == self.flag_cell:
            return ActionFeedback.LEFT_CLICK_FLAG_CELL
        elif self.board_disp[x, y] == self.empty_cell:
            return ActionFeedback.LEFT_CLICK_EMPTY_CELL
        elif self.board_disp[x, y] in "12345678":
            return ActionFeedback.LEFT_CLICK_NUMBER_CELL

        if self.board_true[x, y] == self.mine_cell:
            return self.on_game_over()

        self.board_disp_prev = copy.deepcopy(self.board_disp)
        if self.board_true[x, y] == self.empty_cell:
            self.update_adjacent_cells(x, y)
        # number cell
        else:
            self.board_disp[x, y] = self.board_true[x, y]

        if self.display_on_action:
            self.display()

        if self.check_game_win():
            return ActionFeedback.GAME_WIN

        return ActionFeedback.SUCCESS

    def on_right_click(self, x: int, y: int):
        """
        Right click event handler.
        """
        self.action_history.append(f"R({x},{y})")
        if self.first_move:
            return ActionFeedback.START_BY_RIGHT_CLICK

        x -= 1
        y -= 1

        if not self.is_valid_cell(x, y):
            return ActionFeedback.UNEXIST_CELL

        if self.game_over:
            return self.on_game_over()

        if self.board_disp[x, y] in "12345678":
            return ActionFeedback.RIGHT_CLICK_NUMBER_CELL
        elif self.board_disp[x, y] == self.empty_cell:
            return ActionFeedback.RIGHT_CLICK_EMPTY_CELL

        self.board_disp_prev = copy.deepcopy(self.board_disp)
        if self.board_disp[x, y] == self.unchecked_cell:
            self.board_disp[x, y] = self.flag_cell
        elif self.board_disp[x, y] == self.flag_cell:
            self.board_disp[x, y] = self.unchecked_cell

        if self.display_on_action:
            self.display()

        if self.check_game_win():
            return ActionFeedback.GAME_WIN

        return ActionFeedback.SUCCESS

    def on_middle_click(self, x: int, y: int):
        """
        Middle click event handler.
        """
        self.action_history.append(f"M({x},{y})")
        if self.first_move:
            return ActionFeedback.START_BY_MIDDLE_CLICK

        x -= 1
        y -= 1

        if not self.is_valid_cell(x, y):
            return ActionFeedback.UNEXIST_CELL

        if self.game_over:
            return self.on_game_over()

        if self.board_disp[x, y] == self.empty_cell:
            return ActionFeedback.MIDDLE_CLICK_EMPTY_CELL
        elif self.board_disp[x, y] == self.flag_cell:
            return ActionFeedback.MIDDLE_CLICK_FLAG_CELL
        elif self.board_disp[x, y] == self.unchecked_cell:
            return ActionFeedback.MIDDLE_CLICK_UNCHECKED_CELL

        r_start = max(x - 1, 0)
        r_end = min(x + 2, self.n_rows)
        c_start = max(y - 1, 0)
        c_end = min(y + 2, self.n_cols)

        if not np.sum(self.board_disp[r_start:r_end, c_start:c_end] == self.flag_cell):
            return ActionFeedback.MIDDLE_CLICK_NUMBER_CELL_NO_FLAG

        if np.any(
            self.board_true[r_start:r_end, c_start:c_end][
                self.board_disp[r_start:r_end, c_start:c_end] == self.flag_cell
            ]
            != self.mine_cell
        ):
            self.board_disp_prev = copy.deepcopy(self.board_disp)
            return self.on_game_over()

        if np.sum(self.board_disp[r_start:r_end, c_start:c_end] == self.flag_cell) != int(self.board_true[x, y]):
            return ActionFeedback.MIDDLE_CLICK_NUMBER_CELL_NUMBER_MISMATCH

        self.board_disp_prev = copy.deepcopy(self.board_disp)
        for i, j in product(range(r_start, r_end), range(c_start, c_end)):
            if self.board_disp[i, j] == self.flag_cell:
                continue
            self.update_adjacent_cells(i, j)

        if self.display_on_action:
            self.display()

        if self.check_game_win():
            return ActionFeedback.GAME_WIN

        return ActionFeedback.SUCCESS

    def on_game_over(self):
        self.game_over = True
        self.board_disp = self.board_true
        if self.display_on_action:
            logger.info("Game Over! Please Restart!")
            self.display()
        return ActionFeedback.GAME_OVER

    def check_game_win(self):
        if np.all((self.board_disp == self.flag_cell) == self.board_mine):
            return True

        if not self.strict_winning_condition:
            if np.all((self.board_disp[~self.board_mine] == self.board_true[~self.board_mine])):
                return True

        return False

    @property
    def n_correctly_flagged_mines(self):
        number = int(np.sum(self.board_mine[self.board_disp == self.flag_cell]))
        return number

    def update_adjacent_cells(self, x, y):
        if not self.is_valid_cell(x, y) or not self.board_disp[x, y] == self.unchecked_cell:
            return None

        if self.board_true[x, y] == self.empty_cell:
            self.board_disp[x, y] = self.empty_cell

            for i, j in product(range(x - 1, x + 2), range(y - 1, y + 2)):
                self.update_adjacent_cells(i, j)
        else:
            self.board_disp[x, y] = self.board_true[x, y]

        return None

    def is_mine(self, row, col):
        return self.board_mine[row, col]

    def is_valid_cell(self, row, col):
        return 0 <= row < self.n_rows and 0 <= col < self.n_cols

    def count_mines(self, row, col):
        r_start = max(row - 1, 0)
        r_end = min(row + 2, self.n_rows)
        c_start = max(col - 1, 0)
        c_end = min(col + 2, self.n_cols)
        n_mines = np.sum(self.board_mine[r_start:r_end, c_start:c_end])
        return n_mines

    def add_index(self):
        if self.board_disp_with_index is None:
            self.board_disp_with_index = np.empty((self.n_rows + 1, self.n_cols + 1), dtype=str)
            self.board_disp_with_index.fill(self.empty_cell)
            self.board_disp_with_index[0, :] = np.arange(self.n_cols + 1).astype(str)
            self.board_disp_with_index[1:, 0] = np.arange(1, self.n_rows + 1).astype(str)
        self.board_disp_with_index[1:, 1:] = self.board_disp
        return None

    @property
    def n_revealed_cells(self):
        return int(np.sum(self.board_disp != self.unchecked_cell))

    def to_str_table(self, with_row_column_ids=True) -> str:
        if with_row_column_ids:
            self.add_index()
            str_arr = np.array2string(self.board_disp_with_index, separator=",")
        else:
            str_arr = np.array2string(self.board_disp, separator=",")
        str_arr = re.sub(r"([\[\]])", "", str_arr)
        str_arr = re.sub(
            r"'([1-8%s%s%s])'" % (self.empty_cell, self.flag_cell, self.unchecked_cell), r"`\g<1>'", str_arr
        )
        if with_row_column_ids:
            str_arr = replace_idx_quotes(str_arr)
        str_arr = tailing_comma.sub("", str_arr)
        str_arr = whitespace_start_end.sub("", str_arr)
        return str_arr

    def to_dict_table(self) -> dict:
        coord_value_list = [
            f"({i+1},{j+1}): {self.board_disp[i, j]}" for i, j in product(range(self.n_cols), range(self.n_rows))
        ]
        coord_value_str = "\n".join(coord_value_list)
        return coord_value_str

    def save_board(self, path: str, additional_addribute: Union[list[str], str] = None, **kwargs) -> None:
        if additional_addribute is None:
            additional_addribute = list()
        elif isinstance(additional_addribute, str):
            additional_addribute = [additional_addribute]

        board_dict = {
            "seed": self.seed,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "n_mines": self.n_mines,
            "board_mine": self.board_mine.astype(int).tolist(),
        }
        for addr in additional_addribute:
            board_dict[addr] = getattr(self, addr)
        for k, v in kwargs.items():
            board_dict[k] = v
        save_json(board_dict, path, collapse_level=3)
        return None

    def load_board(self, path: str, load_action_history: bool = False) -> "MineField":
        with open(path, "r", encoding="utf-8") as f:
            board_dict = json.load(f)

        self.seed = board_dict["seed"]
        self.n_rows = board_dict["n_rows"]
        self.n_cols = board_dict["n_cols"]
        self.n_mines = board_dict["n_mines"]

        self.board_true = None
        self.board_disp = None
        self.board_disp_with_index = None

        self.first_move = True
        self.game_over = False

        self.board_mine = np.array(board_dict["board_mine"]).astype(bool)
        self.init_disp_board()

        if load_action_history:
            self.action_history = board_dict.get("action_history", list())

        return self
