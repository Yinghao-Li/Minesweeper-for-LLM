# Minesweeper-for-LLM
This repository provides the code, data, and results for the paper: Assessing Logical Puzzle Solving in Large Language Models: Insights from a Minesweeper Case Study [[arXiv](https://arxiv.org/abs/2311.07387)]

## Requirements

This project is built upon [Python 3.11](https://www.python.org) and [PyQt6](https://www.riverbankcomputing.com/software/pyqt/).
For a complete list of required packages, please find them in the `requirements.txt` file.
It is recommended to create a new `conda` environment for this project as it may be tricky to install PyQt as it can mess up your current dependencies.

```bash
conda create -n ms python=3.11
conda activate ms

pip install -r requirements.txt
```

## Reproducing Results

We have provided our experiment results and some ablation studies in the `./output` folder.
If you are interested in reproducing our results or extending the experiment to a broader set of Minesweeper boards, you can use the Python scripts in `./tasks/` folder.
Specifically,
- `ms.py` runs GPT models on the Minesweeper game.
The arguments of this script are defined in `./src/args.py`.
Examples of running this script are provided in `./scripts`, where `./5x5.table.sh` tests GPTs on $5\times5$ boards with table representation and in natural conversation mode (please refer to the paper for the description of these terms), and `./5x5.coord-compact.sh` tests on boards with coordinate representation and in compact history mode.
To run these shell scripts, you can use
```bash
./scripts/5x5.table.sh
```
- `bn.py` implements the "board navigation" task defined in the paper.
- `nc.py` implements the "neighbor counting" task defined in the paper.

Notice that we use corporate GPT APIs, which are slightly different from the general user APIs.
If you are using the same kind of API as ours, you can directly fill in the blanks within the `./reousrces/*.json` files and start running.
If not, you may also need to modify the `src.gpt.GPT.response` function to suit your need.

## Playing Minesweeper on GUI

Currently, we have not implemented a script for just playing Minesweeper with GUI.
But you can still do this by running the `./assist/lable_board.py` script.
Specifically,
```bash
PYTHONPATH="." python ./assist/lable_board.py --data_dir [your data dir] --disable_saving
```
You can either use our provided data or generate Minesweeper boards of your own through `./assist/generate_board.py`.

## Citation

If you find our work helpful, please consider citing it as
```
```