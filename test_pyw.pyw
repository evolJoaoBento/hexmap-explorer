import tkinter as tk
root = tk.Tk()
root.title("PWY Test")
root.geometry("300x100")
tk.Label(root, text="If you see this, .pyw files work!").pack(pady=20)
tk.Button(root, text="Close", command=root.destroy).pack()
root.mainloop()
