import os
import sys

_BASE_DIR = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

import tkinter as tk

from ui.app import App


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()