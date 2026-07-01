import socket
import threading
import traceback
from typing import Dict, Tuple, Set
import config
import crypto
import time
import pickle

HOST = config.SERVER_HOST
PORT = config.SERVER_PORT
BUFFER_SIZE = config.BUFFER_SIZE

# Client structure: username -> (conn, addr, last_seen, current_room)
clients_lock = threading.Lock()
clients: Dict[str, Tuple[socket.socket, Tuple[str, int], float, str]] = {}

# Rooms: room_name -> set of usernames
rooms_lock = threading.Lock()
rooms: Dict[str, Set[str]] = {}

# Ensure default room exists
with rooms_lock:
    rooms.setdefault(config.DEFAULT_ROOM, set())


def send_encrypted(conn: socket.socket, obj: dict):
    """
    Pickle and encrypt object then send length-prefixed bytes.
    """
    token = crypto.encrypt_object(obj)
    length = len(token).to_bytes(8, "big")
    conn.sendall(length + token)


def recv_encrypted(conn: socket.socket):
    """
    Receive length-prefixed encrypted token and decrypt to object.
    """
    try:
        length_bytes = conn.recv(8)
        if not length_bytes:
            return None
        length = int.from_bytes(length_bytes, "big")
        data = b""
        while len(data) < length:
            packet = conn.recv(min(BUFFER_SIZE, length - len(data)))
            if not packet:
                break
            data += packet
        if not data:
            return None
        obj = crypto.decrypt_object(data)
        return obj
    except Exception:
        return None


def broadcast_system(message: str, room: str = None):
    """
    Broadcast a system message to all clients or to a specific room.
    """
    payload = {"type": "system", "message": message, "time": time.time()}
    with clients_lock:
        for user, (conn, addr, _, user_room) in list(clients.items()):
            if room is None or user_room == room:
                try:
                    send_encrypted(conn, payload)
                except Exception:
                    remove_client(user)


def update_user_list(room: str = None):
    """
    Send updated online user list to all clients or to a specific room.
    If room is None, send global user list.
    """
    with clients_lock:
        if room:
            user_list = [u for u, (_, _, _, r) in clients.items() if r == room]
            for user, (conn, addr, _, user_room) in list(clients.items()):
                if user_room == room:
                    try:
                        send_encrypted(conn, {"type": "userlist", "users": user_list, "room": room})
                    except Exception:
                        remove_client(user)
        else:
            user_list = list(clients.keys())
            for user, (conn, addr, _, _) in list(clients.items()):
                try:
                    send_encrypted(conn, {"type": "userlist", "users": user_list, "room": None})
                except Exception:
                    remove_client(user)


def broadcast_room(room: str, payload: dict):
    """
    Send payload to all users in a room.
    """
    with clients_lock:
        for user, (conn, addr, _, user_room) in list(clients.items()):
            if user_room == room:
                try:
                    send_encrypted(conn, payload)
                except Exception:
                    remove_client(user)


def remove_client(username: str):
    """
    Remove client from clients dict and from any room membership.
    """
    with clients_lock:
        if username in clients:
            conn, addr, _, room = clients.pop(username)
            try:
                conn.close()
            except Exception:
                pass
            # Remove from rooms
            with rooms_lock:
                if room and room in rooms and username in rooms[room]:
                    rooms[room].discard(username)
            broadcast_system(f"{username} has left the chat.", room=None)
            # Update user lists for affected room
            update_user_list(room)
            update_user_list(None)


def handle_client(conn: socket.socket, addr: Tuple[str, int]):
    """
    Per-client handler. First message must be login info: {'type':'login','username':...}
    """
    try:
        obj = recv_encrypted(conn)
        if not obj or obj.get("type") != "login":
            conn.close()
            return
        username = obj.get("username")
        # Prevent duplicate login
        with clients_lock:
            if username in clients:
                send_encrypted(conn, {"type": "login_response", "success": False, "message": "Duplicate login detected."})
                conn.close()
                return
            # Default room assignment
            current_room = config.DEFAULT_ROOM
            clients[username] = (conn, addr, time.time(), current_room)
        # Add to room membership
        with rooms_lock:
            rooms.setdefault(current_room, set()).add(username)

        send_encrypted(conn, {"type": "login_response", "success": True, "message": f"Welcome {username}!", "room": current_room})
        broadcast_system(f"{username} has joined the chat.", room=None)
        broadcast_system(f"{username} has joined {current_room}.", room=current_room)
        update_user_list(current_room)
        update_user_list(None)

        # Main loop
        while True:
            data = recv_encrypted(conn)
            if data is None:
                break
            msg_type = data.get("type")
            if msg_type == "msg":
                # Public or private
                target = data.get("target")  # None for public, username for private
                room = data.get("room") or current_room
                payload = {
                    "type": "msg",
                    "from": username,
                    "message": data.get("message"),
                    "time": data.get("time"),
                    "target": target,
                    "room": room
                }
                if target:
                    # Private
                    with clients_lock:
                        if target in clients:
                            target_conn = clients[target][0]
                            try:
                                send_encrypted(target_conn, payload)
                                send_encrypted(conn, payload)  # echo to sender
                            except Exception:
                                remove_client(target)
                        else:
                            send_encrypted(conn, {"type": "system", "message": f"User {target} not online."})
                else:
                    # Broadcast to room
                    with rooms_lock:
                        if room not in rooms:
                            send_encrypted(conn, {"type": "system", "message": f"Room {room} does not exist."})
                        else:
                            broadcast_room(room, payload)
            elif msg_type == "file":
                # File transfer metadata and bytes
                target = data.get("target")
                filename = data.get("filename")
                filesize = data.get("filesize")
                file_bytes = data.get("filebytes")  # bytes
                room = data.get("room") or current_room
                payload = {
                    "type": "file",
                    "from": username,
                    "filename": filename,
                    "filesize": filesize,
                    "filebytes": file_bytes,
                    "time": data.get("time"),
                    "target": target,
                    "room": room
                }
                if target:
                    with clients_lock:
                        if target in clients:
                            try:
                                send_encrypted(clients[target][0], payload)
                                send_encrypted(conn, {"type": "system", "message": f"File sent to {target}."})
                            except Exception:
                                remove_client(target)
                        else:
                            send_encrypted(conn, {"type": "system", "message": f"User {target} not online."})
                else:
                    # Broadcast to room
                    with rooms_lock:
                        if room not in rooms:
                            send_encrypted(conn, {"type": "system", "message": f"Room {room} does not exist."})
                        else:
                            broadcast_room(room, payload)
            elif msg_type == "typing":
                # Broadcast typing status
                target = data.get("target")
                room = data.get("room") or current_room
                payload = {"type": "typing", "from": username, "target": target, "room": room}
                if target:
                    with clients_lock:
                        if target in clients:
                            try:
                                send_encrypted(clients[target][0], payload)
                            except Exception:
                                remove_client(target)
                else:
                    # Broadcast to room
                    with rooms_lock:
                        if room in rooms:
                            broadcast_room(room, payload)
            elif msg_type == "create_room":
                room_name = data.get("room")
                if not room_name:
                    send_encrypted(conn, {"type": "system", "message": "Invalid room name."})
                else:
                    with rooms_lock:
                        if room_name in rooms:
                            send_encrypted(conn, {"type": "system", "message": f"Room {room_name} already exists."})
                        else:
                            rooms[room_name] = set()
                            send_encrypted(conn, {"type": "system", "message": f"Room {room_name} created."})
                            # Notify all clients about new room list
                            with clients_lock:
                                for u, (c, a, _, _) in list(clients.items()):
                                    try:
                                        send_encrypted(c, {"type": "roomlist", "rooms": list(rooms.keys())})
                                    except Exception:
                                        remove_client(u)
            elif msg_type == "join_room":
                room_name = data.get("room")
                if not room_name:
                    send_encrypted(conn, {"type": "system", "message": "Invalid room name."})
                else:
                    with rooms_lock:
                        if room_name not in rooms:
                            send_encrypted(conn, {"type": "system", "message": f"Room {room_name} does not exist."})
                        else:
                            # Update client's current room
                            with clients_lock:
                                if username in clients:
                                    conn_ref, addr_ref, last_seen, prev_room = clients[username]
                                    clients[username] = (conn_ref, addr_ref, time.time(), room_name)
                            # Update room membership sets
                            with rooms_lock:
                                # remove from previous rooms
                                for rname, members in rooms.items():
                                    members.discard(username)
                                rooms[room_name].add(username)
                            broadcast_system(f"{username} has joined {room_name}.", room=room_name)
                            update_user_list(prev_room)
                            update_user_list(room_name)
                            # Send confirmation and room list
                            send_encrypted(conn, {"type": "system", "message": f"Joined room {room_name}.", "room": room_name})
                            # Send updated room list to this client
                            send_encrypted(conn, {"type": "roomlist", "rooms": list(rooms.keys())})
            elif msg_type == "leave_room":
                room_name = data.get("room")
                if not room_name:
                    send_encrypted(conn, {"type": "system", "message": "Invalid room name."})
                else:
                    with rooms_lock:
                        if room_name in rooms and username in rooms[room_name]:
                            rooms[room_name].discard(username)
                    # Set to default room
                    with clients_lock:
                        if username in clients:
                            conn_ref, addr_ref, last_seen, _ = clients[username]
                            clients[username] = (conn_ref, addr_ref, time.time(), config.DEFAULT_ROOM)
                    with rooms_lock:
                        rooms.setdefault(config.DEFAULT_ROOM, set()).add(username)
                    broadcast_system(f"{username} has left {room_name}.", room=room_name)
                    update_user_list(room_name)
                    update_user_list(config.DEFAULT_ROOM)
                    send_encrypted(conn, {"type": "system", "message": f"Left room {room_name}. Now in {config.DEFAULT_ROOM}.", "room": config.DEFAULT_ROOM})
            elif msg_type == "list_rooms":
                with rooms_lock:
                    send_encrypted(conn, {"type": "roomlist", "rooms": list(rooms.keys())})
            elif msg_type == "logout":
                break
            else:
                send_encrypted(conn, {"type": "system", "message": "Unknown message type."})
    except Exception:
        traceback.print_exc()
    finally:
        # Clean up
        try:
            # Find username by conn
            with clients_lock:
                for user, (c, a, _, _) in list(clients.items()):
                    if c == conn:
                        remove_client(user)
                        break
        except Exception:
            pass


def start_server():
    print(f"Starting ChatVerse server on {HOST}:{PORT}")
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(100)
    try:
        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        server_sock.close()


if __name__ == "__main__":
    start_server()
