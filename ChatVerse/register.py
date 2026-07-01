import tkinter as tk
from tkinter import ttk, messagebox
import database
import sys
import os
import config

class RegisterWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChatVerse - Register")
        self.configure(bg=config.THEME["bg"])
        self.geometry("420x360")
        self.resizable(False, False)
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background=config.THEME["bg"], foreground=config.THEME["text"], font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground=config.THEME["card"], foreground=config.THEME["text"])
        style.configure("TButton", background=config.THEME["accent"], foreground=config.THEME["text"], font=("Segoe UI", 10, "bold"))

        frame = ttk.Frame(self, padding=20)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="Create a new ChatVerse account", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(frame, text="Username").grid(row=1, column=0, sticky="w", pady=5)
        self.username = ttk.Entry(frame, width=30)
        self.username.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="Password").grid(row=2, column=0, sticky="w", pady=5)
        self.password = ttk.Entry(frame, width=30, show="*")
        self.password.grid(row=2, column=1, pady=5)

        ttk.Label(frame, text="Confirm Password").grid(row=3, column=0, sticky="w", pady=5)
        self.confirm = ttk.Entry(frame, width=30, show="*")
        self.confirm.grid(row=3, column=1, pady=5)

        self.register_btn = ttk.Button(frame, text="Register", command=self.on_register)
        self.register_btn.grid(row=4, column=0, columnspan=2, pady=15, ipadx=10)

        self.login_btn = ttk.Button(frame, text="Back to Login", command=self.back_to_login)
        self.login_btn.grid(row=5, column=0, columnspan=2, pady=5, ipadx=10)

    def on_register(self):
        username = self.username.get().strip()
        password = self.password.get()
        confirm = self.confirm.get()
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        success, msg = database.register_user(username, password)
        if success:
            messagebox.showinfo("Success", msg)
            self.destroy()
            os.system(f"{sys.executable} login.py")
        else:
            messagebox.showerror("Error", msg)

    def back_to_login(self):
        self.destroy()
        os.system(f"{sys.executable} login.py")

if __name__ == "__main__":
    app = RegisterWindow()
    app.mainloop()
