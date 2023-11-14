from .core import MineField, ActionFeedback

__all__ = ["MineField", "ActionFeedback"]

try:
    from .gui import MinesweeperGUI

    __all__.append("MinesweeperGUI")
except ImportError:
    pass
