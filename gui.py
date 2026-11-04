import os
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from shikaku_press import run_shikakupress


def run_job(count, difficulty, size, seed, outdir):
    s = run_shikakupress(count, outdir, seed=seed, difficulty=difficulty, size=size)
    lines = [f"Puzzles built: {len(s['puzzles'])}", f"Pages: {s['pages']}"]
    for i, p in enumerate(s["puzzles"], 1):
        lines.append(f"  Puzzle {i}: {p['difficulty']}, {p['n']}x{p['n']}, "
                     f"{p['rect_count']} rectangles, unique solution proven")
    lines.append(f"PDF: {s['pdf_path']}")
    return lines


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ShikakuPress")
        self.geometry("640x520")
        self.resizable(False, False)
        self.count = tk.StringVar(value="50")
        self.difficulty = tk.StringVar(value="Mixed")
        self.size = tk.StringVar(value="Mixed")
        self.seed = tk.StringVar(value="42")
        for label, var in [("Puzzles:", self.count),
                           ("Difficulty (Easy/Medium/Hard/Mixed):", self.difficulty),
                           ("Size (6/8/10/Mixed):", self.size),
                           ("Seed:", self.seed)]:
            row = tk.Frame(self); row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=label, width=34, anchor="w").pack(side="left")
            tk.Entry(row, textvariable=var, width=10).pack(side="left")
        tk.Button(self, text="Build the book", font=("Segoe UI", 11, "bold"),
                  command=self.start).pack(pady=10)
        self.log = scrolledtext.ScrolledText(self, width=76, height=16,
                                             font=("Consolas", 9))
        self.log.pack(padx=12, pady=4)
        self.write("Every puzzle starts as a rectangle partition of the whole grid -- then an independent exact-cover solver re-counts the tilings from the printed clues alone. Only puzzles with exactly one tiling ship.")

    def write(self, msg):
        self.log.insert(tk.END, str(msg) + "\n")
        self.log.see(tk.END)
        self.update_idletasks()

    def collect(self):
        diff = self.difficulty.get().strip().capitalize()
        if diff not in ("Easy", "Medium", "Hard", "Mixed"):
            raise ValueError("Difficulty must be Easy, Medium, Hard or Mixed.")
        size = self.size.get().strip().capitalize()
        if size not in ("6", "8", "10", "Mixed"):
            raise ValueError("Size must be 6, 8, 10 or Mixed.")
        return (int(self.count.get()), diff, size, int(self.seed.get()),
                os.path.join(os.getcwd(), "shikakupress_out"))

    def start(self):
        try:
            args = self.collect()
        except Exception as e:
            messagebox.showerror("ShikakuPress", str(e))
            return

        def work():
            try:
                for ln in run_job(*args):
                    self.write(ln)
            except Exception as e:
                self.write(f"ERROR: {e}")

        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
