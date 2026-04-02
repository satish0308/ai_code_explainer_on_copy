"""Run this standalone to verify which font-resize method works on your system."""
import tkinter as tk
from tkinter import scrolledtext

root = tk.Tk()
root.title("Font Resize Test")
root.geometry("600x500")
root.configure(bg="#1e1e2e")

size = [14]
SAMPLE = (
    "def fibonacci(n):\n"
    "    if n <= 1:\n"
    "        return n\n"
    "    a, b = 0, 1\n"
    "    for _ in range(2, n + 1):\n"
    "        a, b = b, a + b\n"
    "    return b\n\n"
    "This function computes the nth Fibonacci number iteratively.\n"
    "It avoids recursion so it runs in O(n) time with O(1) space.\n"
) * 3

txt = scrolledtext.ScrolledText(root, bg="#1e1e2e", fg="#cdd6f4",
                                 font=("Segoe UI", size[0]), wrap="word",
                                 relief="flat", state="disabled")
txt.pack(fill="both", expand=True, padx=10, pady=10)

# Insert ALL text tagged with "body"
txt.tag_configure("body", font=("Segoe UI", size[0]), foreground="#cdd6f4")
txt.configure(state="normal")
txt.insert("end", SAMPLE, "body")
txt.configure(state="disabled")

result_lbl = tk.Label(root, text="Click buttons — does the text size change?",
                      bg="#1e1e2e", fg="#89b4fa", font=("Segoe UI", 11))
result_lbl.pack(pady=4)

def method_tag(delta):
    """Method A: tag_configure only."""
    size[0] = max(8, min(40, size[0] + delta))
    txt.tag_configure("body", font=("Segoe UI", size[0]))
    result_lbl.config(text=f"Method A (tag_configure): {size[0]}pt")

def method_full(delta):
    """Method B: save text, clear, set widget font, reinsert."""
    size[0] = max(8, min(40, size[0] + delta))
    txt.configure(state="normal")
    content = txt.get("1.0", "end-1c")
    txt.delete("1.0", "end")
    txt.configure(font=("Segoe UI", size[0]))
    txt.insert("1.0", content)
    txt.configure(state="disabled")
    result_lbl.config(text=f"Method B (clear+reinsert): {size[0]}pt")

bar = tk.Frame(root, bg="#181825", pady=8)
bar.pack(fill="x")
tk.Label(bar, text="Method A (tag_configure):", bg="#181825", fg="#6c7086",
         font=("Segoe UI", 10)).pack(side="left", padx=8)
tk.Button(bar, text="A−", command=lambda: method_tag(-2),
          bg="#313244", fg="#cdd6f4", relief="flat", padx=8).pack(side="left")
tk.Button(bar, text="A+", command=lambda: method_tag(+2),
          bg="#313244", fg="#cdd6f4", relief="flat", padx=8).pack(side="left", padx=4)

tk.Label(bar, text="|", bg="#181825", fg="#45475a").pack(side="left", padx=4)
tk.Label(bar, text="Method B (clear+reinsert):", bg="#181825", fg="#6c7086",
         font=("Segoe UI", 10)).pack(side="left", padx=4)
tk.Button(bar, text="B−", command=lambda: method_full(-2),
          bg="#313244", fg="#a6e3a1", relief="flat", padx=8).pack(side="left")
tk.Button(bar, text="B+", command=lambda: method_full(+2),
          bg="#313244", fg="#a6e3a1", relief="flat", padx=8).pack(side="left", padx=4)

root.mainloop()
