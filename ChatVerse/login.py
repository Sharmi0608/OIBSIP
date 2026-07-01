import tkinter as tk
from tkinter import ttk, messagebox
import database
import os
import sys
import config
import subprocess

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChatVerse - Login")
        self.configure(bg=config.THEME["bg"])
        self.geometry("420x320")
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

        ttk.Label(frame, text="Welcome to ChatVerse", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(frame, text="Username").grid(row=1, column=0, sticky="w", pady=5)
        self.username = ttk.Entry(frame, width=30)
        self.username.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="Password").grid(row=2, column=0, sticky="w", pady=5)
        self.password = ttk.Entry(frame, width=30, show="*")
        self.password.grid(row=2, column=1, pady=5)

        self.login_btn = ttk.Button(frame, text="Login", command=self.on_login)
        self.login_btn.grid(row=3, column=0, columnspan=2, pady=12, ipadx=10)

        self.register_btn = ttk.Button(frame, text="Register", command=self.open_register)
        self.register_btn.grid(row=4, column=0, columnspan=2, pady=5, ipadx=10)

    def on_login(self):
        username = self.username.get().strip()
        password = self.password.get()
        success, msg = database.authenticate_user(username, password)
        if success:
            # Launch client with username argument
            self.destroy()
            # Use subprocess to run client in same interpreter
            subprocess.Popen([sys.executable, "client.py", username])
        else:
            messagebox.showerror("Login Failed", msg)

    def open_register(self):
        self.destroy()
        os.system(f"{sys.executable} register.py")

if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
