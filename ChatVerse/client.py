import socket
import threading
import sys
import os
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import config
import crypto
from plyer import notification
import datetime

# Networking
SERVER_HOST = "127.0.0.1"
SERVER_PORT = config.SERVER_PORT
BUFFER_SIZE = config.BUFFER_SIZE

# UI constants
THEME = config.THEME
HISTORY_DIR = config.HISTORY_DIR
RECEIVED_DIR = config.RECEIVED_DIR
SENT_DIR = config.SENT_DIR

# Simple emoji list
EMOJIS = ["😀", "😂", "😍", "👍", "🙏", "🔥", "🎉", "😢", "😎", "🤝","❤️"]

class ChatClient:
    def __init__(self, username: str):
        self.username = username
        self.sock = None
        self.running = False
        self.users = []
        self.rooms = [config.DEFAULT_ROOM]
        self.current_room = config.DEFAULT_ROOM
        self.history_file = HISTORY_DIR / f"{self.username}__{self.current_room}.txt"
        self.setup_ui()
        self.connect_to_server()

    # ---------------- Networking ----------------
    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            # Send login
            self.send_encrypted({"type": "login", "username": self.username})
            resp = self.recv_encrypted()
            if not resp or not resp.get("success"):
                messagebox.showerror("Login Failed", resp.get("message", "Unknown error"))
                self.root.destroy()
                return
            # Server may send initial room
            self.current_room = resp.get("room", config.DEFAULT_ROOM)
            self.running = True
            threading.Thread(target=self.listen_thread, daemon=True).start()
            # Request room list
            self.send_encrypted({"type": "list_rooms"})
            self.load_history()
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", "Unable to connect to server.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.root.destroy()

    def send_encrypted(self, obj: dict):
        token = crypto.encrypt_object(obj)
        length = len(token).to_bytes(8, "big")
        self.sock.sendall(length + token)

    def recv_encrypted(self):
        try:
            length_bytes = self.sock.recv(8)
            if not length_bytes:
                return None
            length = int.from_bytes(length_bytes, "big")
            data = b""
            while len(data) < length:
                packet = self.sock.recv(min(BUFFER_SIZE, length - len(data)))
                if not packet:
                    break
                data += packet
            if not data:
                return None
            obj = crypto.decrypt_object(data)
            return obj
        except Exception:
            return None

    def listen_thread(self):
        while self.running:
            try:
                obj = self.recv_encrypted()
                if obj is None:
                    break
                self.handle_server_message(obj)
            except Exception:
                break
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        self.append_system("Disconnected from server.")

    # ---------------- Message Handling ----------------
    def handle_server_message(self, obj: dict):
        mtype = obj.get("type")
        if mtype == "system":
            self.append_system(obj.get("message"))
        elif mtype == "userlist":
            # If room provided, update users for that room
            room = obj.get("room")
            if room and room == self.current_room:
                self.users = obj.get("users", [])
                self.update_user_panel()
            elif room is None:
                # global user list not used for panel; ignore or could be used
                pass
        elif mtype == "roomlist":
            self.rooms = obj.get("rooms", [])
            self.update_room_panel()
        elif mtype == "msg":
            sender = obj.get("from")
            message = obj.get("message")
            target = obj.get("target")
            room = obj.get("room", self.current_room)
            timestamp = obj.get("time", time.time())
            timestr = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            if target:
                # Private
                display = f"[{timestr}] (Private) {sender} -> {self.username}: {message}"
                self.append_chat(display)
                notification.notify(title=f"Private from {sender}", message=message, timeout=3)
            else:
                # Room message: only display if it's for current room
                if room == self.current_room:
                    display = f"[{timestr}] [{room}] {sender}: {message}"
                    self.append_chat(display)
                    notification.notify(title=f"{room} - {sender}", message=message, timeout=3)
                    self.save_history_line(display)
            # If message is for another room, optionally ignore or store; we store to history file for that room
            if not target and room != self.current_room:
                # Save to that room's history file
                hist = HISTORY_DIR / f"{self.username}__{room}.txt"
                try:
                    with open(hist, "a", encoding="utf-8") as f:
                        f.write(f"[{timestr}] [{room}] {sender}: {message}\n")
                except Exception:
                    pass
        elif mtype == "file":
            sender = obj.get("from")
            filename = obj.get("filename")
            filebytes = obj.get("filebytes")
            room = obj.get("room", self.current_room)
            timestamp = obj.get("time", time.time())
            timestr = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            save_path = RECEIVED_DIR / f"{int(time.time())}_{filename}"
            try:
                with open(save_path, "wb") as f:
                    f.write(filebytes)
                display = f"[{timestr}] [{room}] {sender} sent file: {filename} (saved to {save_path})"
                if room == self.current_room or obj.get("target") == self.username:
                    self.append_chat(display)
                    notification.notify(title="File received", message=f"{sender} sent {filename}", timeout=4)
                    self.save_history_line(display)
                else:
                    # Save to history for that room
                    hist = HISTORY_DIR / f"{self.username}__{room}.txt"
                    try:
                        with open(hist, "a", encoding="utf-8") as f:
                            f.write(display + "\n")
                    except Exception:
                        pass
            except Exception as e:
                self.append_system(f"Failed to save file: {e}")
        elif mtype == "typing":
            sender = obj.get("from")
            room = obj.get("room")
            target = obj.get("target")
            if (room is None or room == self.current_room) and (target is None or target == self.username):
                self.show_typing(sender)
        else:
            pass

    # ---------------- UI ----------------
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title(f"ChatVerse - {self.username}")
        self.root.configure(bg=THEME["bg"])
        self.root.geometry("1000x640")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Layout frames
        left_frame = tk.Frame(self.root, bg=THEME["panel"], width=260)
        left_frame.pack(side="left", fill="y")

        center_frame = tk.Frame(self.root, bg=THEME["bg"])
        center_frame.pack(side="left", fill="both", expand=True)

        # Left - rooms and online users
        tk.Label(left_frame, text="Rooms", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).pack(pady=(10, 2))
        self.room_listbox = tk.Listbox(left_frame, bg=THEME["card"], fg=THEME["text"], selectbackground=THEME["accent"], relief="flat", height=8)
        self.room_listbox.pack(fill="x", padx=10, pady=(0, 8))
        self.room_listbox.bind("<<ListboxSelect>>", lambda e: self.on_room_select())

        room_controls = tk.Frame(left_frame, bg=THEME["panel"])
        room_controls.pack(fill="x", padx=10)
        self.new_room_entry = tk.Entry(room_controls, bg=THEME["card"], fg=THEME["text"])
        self.new_room_entry.pack(side="left", fill="x", expand=True)
        tk.Button(room_controls, text="Create", command=self.create_room, bg=THEME["accent"], fg=THEME["text"]).pack(side="left", padx=(6, 0))

        tk.Label(left_frame, text="Online Users (in room)", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).pack(pady=(12, 2))
        self.user_listbox = tk.Listbox(left_frame, bg=THEME["card"], fg=THEME["text"], selectbackground=THEME["accent"], relief="flat")
        self.user_listbox.pack(fill="both", expand=True, padx=10, pady=5)

        # Center - chat display
        header_frame = tk.Frame(center_frame, bg=THEME["bg"])
        header_frame.pack(fill="x", padx=10, pady=(10, 0))
        self.room_label_var = tk.StringVar(value=f"Room: {self.current_room}")
        tk.Label(header_frame, textvariable=self.room_label_var, bg=THEME["bg"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).pack(side="left")

        self.chat_display = scrolledtext.ScrolledText(center_frame, bg=THEME["card"], fg=THEME["text"], state="disabled", wrap="word")
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=(6, 5))

        # Typing indicator
        self.typing_var = tk.StringVar(value="")
        self.typing_label = tk.Label(center_frame, textvariable=self.typing_var, bg=THEME["bg"], fg=THEME["muted"], anchor="w")
        self.typing_label.pack(fill="x", padx=12)

        # Bottom controls
        bottom_frame = tk.Frame(center_frame, bg=THEME["bg"])
        bottom_frame.pack(fill="x", padx=10, pady=10)

        self.emoji_btn = tk.Button(bottom_frame, text="😊", command=self.open_emoji_picker, bg=THEME["panel"], fg=THEME["text"])
        self.emoji_btn.pack(side="left", padx=(0, 6))

        self.file_btn = tk.Button(bottom_frame, text="📎", command=self.send_file_dialog, bg=THEME["panel"], fg=THEME["text"])
        self.file_btn.pack(side="left", padx=(0, 6))

        self.message_entry = tk.Entry(bottom_frame, bg=THEME["card"], fg=THEME["text"])
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        self.message_entry.bind("<KeyPress>", lambda e: self.send_typing())

        self.send_btn = tk.Button(bottom_frame, text="Send", command=self.send_message, bg=THEME["accent"], fg=THEME["text"])
        self.send_btn.pack(side="left")

        # Menu
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Clear Chat", command=self.clear_chat)
        filemenu.add_command(label="Export History", command=self.export_history)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    def update_room_panel(self):
        self.room_listbox.delete(0, tk.END)
        for r in sorted(self.rooms):
            self.room_listbox.insert(tk.END, r)
        # Ensure current room selected
        try:
            idx = self.rooms.index(self.current_room)
            self.room_listbox.selection_clear(0, tk.END)
            self.room_listbox.selection_set(idx)
            self.room_listbox.see(idx)
        except ValueError:
            pass
        self.room_label_var.set(f"Room: {self.current_room}")

    def update_user_panel(self):
        self.user_listbox.delete(0, tk.END)
        for u in sorted(self.users):
            self.user_listbox.insert(tk.END, u)

    def append_chat(self, text: str):
        self.chat_display.configure(state="normal")
        self.chat_display.insert(tk.END, text + "\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see(tk.END)

    def append_system(self, text: str):
        self.append_chat(f"[SYSTEM] {text}")

    def save_history_line(self, line: str):
        try:
            hist = HISTORY_DIR / f"{self.username}__{self.current_room}.txt"
            with open(hist, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def load_history(self):
        self.history_file = HISTORY_DIR / f"{self.username}__{self.current_room}.txt"
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    for line in f:
                        self.append_chat(line.rstrip("\n"))
            except Exception:
                pass

    def clear_chat(self):
        if messagebox.askyesno("Clear Chat", "Clear chat window (history file will remain)?"):
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.configure(state="disabled")

    def export_history(self):
        try:
            export_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
            if export_path:
                hist = HISTORY_DIR / f"{self.username}__{self.current_room}.txt"
                with open(hist, "r", encoding="utf-8") as src, open(export_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                messagebox.showinfo("Exported", f"History exported to {export_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Actions ----------------
    def send_message(self):
        text = self.message_entry.get().strip()
        if not text:
            return
        # Check for private message format: @username message
        target = None
        if text.startswith("@"):
            parts = text.split(" ", 1)
            if len(parts) == 2:
                target_candidate = parts[0][1:]
                if target_candidate in self.users:
                    target = target_candidate
                    text = parts[1]
        payload = {"type": "msg", "message": text, "time": time.time(), "target": target, "room": self.current_room}
        try:
            self.send_encrypted(payload)
            self.message_entry.delete(0, tk.END)
        except Exception:
            self.append_system("Failed to send message.")

    def send_typing(self):
        try:
            self.send_encrypted({"type": "typing", "target": None, "room": self.current_room})
        except Exception:
            pass

    def show_typing(self, username):
        self.typing_var.set(f"{username} is typing...")
        self.root.after(1500, lambda: self.typing_var.set(""))

    def send_file_dialog(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        filename = os.path.basename(file_path)
        ext = Path(filename).suffix.lower()
        if ext not in config.ALLOWED_EXT:
            messagebox.showerror("Unsupported", "File type not supported.")
            return
        # Optionally choose recipient
        sel = self.user_listbox.curselection()
        target = None
        if sel:
            target = self.user_listbox.get(sel[0])
            if target == self.username:
                target = None
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            payload = {"type": "file", "filename": filename, "filesize": len(data), "filebytes": data, "time": time.time(), "target": target, "room": self.current_room}
            self.send_encrypted(payload)
            # Save copy to sent folder
            sent_path = SENT_DIR / f"{int(time.time())}_{filename}"
            with open(sent_path, "wb") as sf:
                sf.write(data)
            self.append_system(f"Sent file {filename} (saved copy to {sent_path})")
        except Exception as e:
            self.append_system(f"Failed to send file: {e}")

    def open_emoji_picker(self):
        win = tk.Toplevel(self.root)
        win.title("Emoji Picker")
        win.configure(bg=THEME["bg"])
        for i, e in enumerate(EMOJIS):
            btn = tk.Button(win, text=e, font=("Segoe UI", 14), command=lambda em=e: self.insert_emoji(em), bg=THEME["panel"], fg=THEME["text"])
            btn.grid(row=i // 6, column=i % 6, padx=6, pady=6)

    def insert_emoji(self, emoji):
        cur = self.message_entry.get()
        self.message_entry.delete(0, tk.END)
        self.message_entry.insert(0, cur + emoji)

    def on_room_select(self):
        sel = self.room_listbox.curselection()
        if not sel:
            return
        room = self.room_listbox.get(sel[0])
        if room == self.current_room:
            return
        # Send join request to server
        try:
            self.send_encrypted({"type": "join_room", "room": room})
            # Update local current room after server confirms; server will send system message and roomlist
            # But optimistically set current room to show UI change
            self.current_room = room
            self.room_label_var.set(f"Room: {self.current_room}")
            # Load history for new room
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.configure(state="disabled")
            self.load_history()
            # Request user list update for this room
            self.send_encrypted({"type": "list_rooms"})
            self.send_encrypted({"type": "list_rooms"})  # server will respond with roomlist and userlist updates
        except Exception:
            self.append_system("Failed to switch rooms.")

    def create_room(self):
        name = self.new_room_entry.get().strip()
        if not name:
            messagebox.showerror("Invalid", "Room name cannot be empty.")
            return
        try:
            self.send_encrypted({"type": "create_room", "room": name})
            self.new_room_entry.delete(0, tk.END)
            # Ask server for updated room list
            self.send_encrypted({"type": "list_rooms"})
        except Exception:
            self.append_system("Failed to create room.")

    def on_close(self):
        try:
            if self.running:
                self.send_encrypted({"type": "logout"})
        except Exception:
            pass
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <username>")
        sys.exit(1)
    username = sys.argv[1]
    client = ChatClient(username)
    client.run()
