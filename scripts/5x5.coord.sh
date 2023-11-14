#!/bin/bash

# Quit if there are any errors
set -e

PYTHONPATH="." python ./tasks/test_5x5.py \
  --board_path_or_dir "./data/5x5-4-test/" \
  --output_dir "./output/board-solve-update/5x5-4-coord/" \
  --max_steps 10 \
  --use_row_column_indices false \
  --use_compressed_history false \
  --represent_board_as_coordinate true \
  --strict_winning_condition true