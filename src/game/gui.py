"""
# Author: Yinghao Li
# Modified: October 27th, 2023
# ---------------------------------------
# Description: GUI for Minesweeper
"""

import numpy as np
import logging

from .core import MineField, ActionFeedback
from PyQt6.QtWidgets import QMainWindow, QPushButton
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QFont, QColor

logger = logging.getLogger(__name__)

# Define colors for numbers 1 through 8
NUMBER_COLORS = {
    "1": QColor(0, 0, 255),  # Blue
    "2": QColor(0, 128, 0),  # Green
    "3": QColor(255, 0, 0),  # Red
    "4": QColor(0, 0, 128),  # Navy
    "5": QColor(128, 0, 0),  # Maroon
    "6": QColor(0, 128, 128),  # Teal
    "7": QColor(0, 0, 0),  # Black
    "8": QColor(128, 128, 128),  # Gray
}


class Cell(QPushButton):
    right_clicked = pyqtSignal()  # custom signal for right click
    middle_clicked = pyqtSignal()  # custom signal for middle click

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flagged = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()

        elif event.button() == Qt.MouseButton.MiddleButton:
            self.middle_clicked.emit()

        else:
            super().mousePressEvent(event)  # call the original method to handle other types of clicks

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.flagged:
            self.draw_flag()

    def draw_flag(self):
        painter = QPainter(self)
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(153, 0, 0))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "F")  # Draw "F" centered in the button's rectangle
        painter.end()


class MinesweeperGUI(QMainWindow):
    def __init__(self, m: MineField):
        super().__init__()
        self.m = m

        self.n_rows = m.n_rows
        self.n_cols = m.n_cols
        self.n_mines = m.n_mines

        self.cell_size = 40

        self.cells = None
        self.init_ui()

    def init_ui(self):
        self.setGeometry(100, 100, 400, 400)
        self.setWindowTitle("Minesweeper")
        self.setFixedSize(QSize(self.n_cols * self.cell_size, self.n_rows * self.cell_size))

        self.cells = list()

        # x-axis, up to down
        for x in range(self.n_cols):
            self.cells.append(list())

            # y-axis, left to right
            for y in range(self.n_rows):
                btn = Cell(" ", self)
                btn.setGeometry(y * self.cell_size, x * self.cell_size, self.cell_size, self.cell_size)
                btn.setStyleSheet("background-color: #C0C0C0")

                btn.clicked.connect(self.on_left_click)
                btn.right_clicked.connect(self.on_right_click)
                btn.middle_clicked.connect(self.on_middle_click)
                self.cells[x].append(btn)

    def on_left_click(self):
        btn = self.sender()
        x, y = self.check_cell_coord(btn)
        feedback = self.m.on_left_click(x + 1, y + 1)
        if feedback == ActionFeedback.SUCCESS:
            self.update_cells_by_content()
        elif feedback == ActionFeedback.GAME_OVER:
            self.reveal_mines(x, y)
            self.setWindowTitle("Game Over!")
        elif feedback == ActionFeedback.GAME_WIN:
            self.update_cells_by_content()
            self.setWindowTitle("Win!")

        logger.info(feedback)

        return None

    def on_right_click(self):
        btn = self.sender()
        x, y = self.check_cell_coord(btn)
        feedback = self.m.on_right_click(x + 1, y + 1)
        if feedback == ActionFeedback.SUCCESS:
            # draw a flag in the button here
            btn.flagged = not btn.flagged
            btn.repaint()
        elif feedback == ActionFeedback.GAME_WIN:
            self.update_cells_by_content()
            self.setWindowTitle("Win!")
        logger.info(feedback)
        return None

    def on_middle_click(self):
        btn = self.sender()
        x, y = self.check_cell_coord(btn)
        feedback = self.m.on_middle_click(x + 1, y + 1)
        if feedback == ActionFeedback.SUCCESS:
            self.update_cells_by_content()
        elif feedback == ActionFeedback.GAME_OVER:
            self.reveal_mines(x, y)
            self.setWindowTitle("Game Over!")
        elif feedback == ActionFeedback.GAME_WIN:
            self.update_cells_by_content()
            self.setWindowTitle("Win!")

        logger.info(feedback)

        return None

    def check_cell_coord(self, button):
        y = button.geometry().x() // self.cell_size
        x = button.geometry().y() // self.cell_size
        logger.info(f"clicked on {x}, {y}")

        return x, y

    def update_cells_by_content(self):
        updated_cells_x, updated_cells_y = np.where(self.m.board_disp != self.m.board_disp_prev)
        for x, y in zip(updated_cells_x, updated_cells_y):
            value = str(self.m.board_disp[x, y])
            if value == self.m.empty_cell:
                value = " "
            self.cells[x][y].setText(value)

            # Update font and color based on the content
            font = QFont()
            font.setPointSize(20)
            self.cells[x][y].setFont(font)

            text_color = NUMBER_COLORS.get(value, QColor(0, 0, 0))  # Default to black if value not found

            # Get current background color and lighten it
            bg_color = QColor(self.cells[x][y].palette().button().color())
            bg_color.setRed(min(bg_color.red() + 30, 255))
            bg_color.setGreen(min(bg_color.green() + 30, 255))
            bg_color.setBlue(min(bg_color.blue() + 30, 255))

            self.cells[x][y].setStyleSheet(
                f"background-color: rgb({bg_color.red()}, {bg_color.green()}, {bg_color.blue()});"
                f"color: rgb({text_color.red()}, {text_color.green()}, {text_color.blue()});"
            )

        return self

    def reveal_mines(self, clicked_x, clicked_y):
        # Set the background color of the clicked cell to dark red while preserving its text color
        bg_color = QColor(200, 0, 0)  # dark red
        text_color = QColor(self.cells[clicked_x][clicked_y].palette().buttonText().color())
        self.cells[clicked_x][clicked_y].setStyleSheet(
            f"background-color: rgb({bg_color.red()}, {bg_color.green()}, {bg_color.blue()});"
            f"color: rgb({text_color.red()}, {text_color.green()}, {text_color.blue()});"
        )

        mine_cells_x, mine_cells_y = np.where(self.m.board_mine)

        for x, y in zip(mine_cells_x, mine_cells_y):
            if self.cells[x][y].flagged:
                continue
            self.cells[x][y].setText("#")

            # Update font and color based on the content
            font = QFont()
            font.setPointSize(20)
            self.cells[x][y].setFont(font)

            color = QColor(0, 0, 0)

            bg_color = QColor(self.cells[x][y].palette().button().color())
            self.cells[x][y].setStyleSheet(
                f"background-color: rgb({bg_color.red()}, {bg_color.green()}, {bg_color.blue()});"
                f"color: rgb({color.red()}, {color.green()}, {color.blue()});"
            )

        return self
