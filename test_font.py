import tkinter as tk
import tkinter.font as tkFont

root = tk.Tk()

font = tkFont.Font(family="Arial", size=14)

label = tk.Label(root, text="Test Text", font=font)
label.pack()


def increase():
    font.configure(size=font.cget("size") + 5)
    print("Size:", font.cget("size"))


tk.Button(root, text="Increase", command=increase).pack()

root.mainloop()
