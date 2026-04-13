import socket
import threading
import json
from collections import Counter
from SQL import SQLiteHelper

# Initialize SQLiteHelper (thread-safe access)
db = SQLiteHelper("users.db", check_same_thread=False)

# Create tables if not exist
db.execute("""
CREATE TABLE IF NOT EXISTS users(
    email TEXT,
    name TEXT,
    password TEXT,
    id INTEGER,
    friends TEXT,
    offline TEXT
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS chats(
    list TEXT,
    text TEXT
)
""")

online = {}
rooms = {}

def find_key_dict(dct, value):
    for key, val in dct.items():
        if val == value:
            return key

def create_user(email, name, password):
    # Determine new user ID by counting existing users
    user_id = db.count("users")
    empty_list = []
    # Insert new user with parameterized query
    db.execute(
        "INSERT INTO users(email, name, password, id, friends, offline) VALUES (?, ?, ?, ?, ?, ?)",
        (email, name, password, user_id, json.dumps(empty_list), "")
    )
    return user_id

def verify_user(email, name, password):
    row = db.fetchone("SELECT id FROM users WHERE email = ?", (email,))
    if not row:
        return None  # email not found => new user
    # Check name and password
    row = db.fetchone(
        "SELECT id FROM users WHERE name = ? AND password = ?",
        (name, password)
    )
    return row[0] if row else -1  # -1 means wrong password

def handle_client(client, addr, _):
    while True:
        data = client.recv(2048).decode()
        if not data or data == "EXIT":
            print(f"{addr} Disconnected")
            key = find_key_dict(online, (client, addr))
            if key is not None:
                online.pop(key)
            client.send("EXIT".encode())
            client.close()
            break

        if data == "CLEAR":
            # Delete all records
            db.execute("DELETE FROM users")
            db.execute("DELETE FROM chats")
            continue

        parts = data.split("|")

        if parts[0] == "OFFLINE":
            user_id = int(parts[1])
            offline_msg = db.fetchone("SELECT offline FROM users WHERE id = ?", (user_id,))
            offline_text = offline_msg[0] if offline_msg else ""
            # Send first pending offline message, then clear it from DB
            if offline_text:
                first_line = offline_text.split("\n", 1)[0]
                if first_line:
                    client.send(first_line.encode())
                # Remove the send message line
                remaining = offline_text[len(first_line)+1:] if "\n" in offline_text else ""
                db.execute("UPDATE users SET offline = ? WHERE id = ?", (remaining, user_id))
            online[user_id] = (client, addr)

        elif parts[0] == "DONE":
            user_id = int(parts[1])
            # Same as OFFLINE handler
            offline_msg = db.fetchone("SELECT offline FROM users WHERE id = ?", (user_id,))
            offline_text = offline_msg[0] if offline_msg else ""
            if offline_text:
                first_line = offline_text.split("\n", 1)[0]
                if first_line:
                    client.send(first_line.encode())
                remaining = offline_text[len(first_line)+1:] if "\n" in offline_text else ""
                db.execute("UPDATE users SET offline = ? WHERE id = ?", (remaining, user_id))

        elif parts[0] == "LOGIN":
            email, name, password = parts[1], parts[2], parts[3]
            result = verify_user(email, name, password)
            if result is None:
                # New user
                new_id = create_user(email, name, password)
                client.send(f"NEW|{new_id}".encode())
            elif result == -1:
                client.send("NO".encode())  # wrong password
            else:
                client.send(f"OK|{result}".encode())

        elif parts[0] == "CHAT_START":
            f_list = json.loads(parts[1])
            rows = db.fetchall("SELECT list FROM chats")
            text = "HOW????"
            real_list = f_list
            for row in rows:
                l = row[0]
                # Compare lists irrespective of order
                if Counter(f_list) == Counter(json.loads(l)):
                    chat_text = db.fetchone("SELECT text FROM chats WHERE list = ?", (l,))
                    text = l + ":\n" + (chat_text[0] if chat_text else "")
                    real_list = l
                    break
            client.send(f"CHAT_START|{real_list}|{text}".encode())

        elif parts[0] == "CHAT":
            sender_id = parts[1]
            lst = json.loads(parts[2])
            message = parts[3]

            name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (sender_id,))
            sender_name = name_row[0] if name_row else ""
            upload = sender_name + "> " + message

            current = db.fetchone("SELECT text FROM chats WHERE list = ?", (json.dumps(lst),))
            current_text = current[0] if current else ""
            new_text = current_text + "\n" + upload

            db.execute(
                "UPDATE chats SET text = ? WHERE list = ?",
                (new_text, json.dumps(lst))
            )

            # Notify other participants
            for uid in lst:
                if str(uid) != sender_id and uid in online:
                    client_F = online[uid][0]
                    client_F.send(f"CHAT|{sender_id}|{lst}".encode())

        elif parts[0] == "GROUP":
            lst = json.loads(parts[1])
            group_name = parts[2]
            # Create a new chat entry for the group
            db.execute("INSERT INTO chats(list, text) VALUES (?, ?)", (json.dumps(lst), ""))

            for user_id in lst:
                fake_lst = lst.copy()
                fake_lst.remove(user_id)
                # Update friends list for each user
                row = db.fetchone("SELECT friends FROM users WHERE id = ?", (user_id,))
                friends = json.loads(row[0]) if row and row[0] else []
                friends.append([group_name, fake_lst])
                db.execute("UPDATE users SET friends = ? WHERE id = ?", (json.dumps(friends), user_id))

                if user_id not in online:
                    # Store offline notification
                    off_row = db.fetchone("SELECT offline FROM users WHERE id = ?", (user_id,))
                    offline_old = off_row[0] if off_row else ""
                    new_offline = offline_old + f"ADDED|{group_name}\n"
                    db.execute("UPDATE users SET offline = ? WHERE id = ?", (new_offline, user_id))
                else:
                    client_F = online[user_id][0]
                    client_F.send(f"ADDED|{group_name}".encode())

        elif parts[0] == "CMD":
            user_id = int(parts[1])
            cmd = parts[2]

            if cmd == "list":
                row = db.fetchone("SELECT friends FROM users WHERE id = ?", (user_id,))
                friends_list = json.loads(row[0]) if row and row[0] else []
                client.send(f"FRIENDS|{json.dumps(friends_list)}".encode())

            elif cmd == "online":
                client.send(f"ONLINE|{online}".encode())

            elif cmd == "me":
                name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (user_id,))
                user_name = name_row[0] if name_row else ""
                client.send(f"ME|{user_id}:{addr}|{user_name}".encode())

            elif cmd.startswith("add "):
                friend_str = cmd[4:].strip()
                if not friend_str.isdigit():
                    client.send("INVALID".encode())
                    continue
                friend_id = int(friend_str)

                # Get current max ID
                max_id = db.count("users")
                row = db.fetchone("SELECT friends FROM users WHERE id = ?", (user_id,))
                current_friends = json.loads(row[0]) if row and row[0] else []

                if friend_id < max_id and friend_id not in current_friends and friend_id != user_id:
                    if friend_id in online:
                        # Send friend request online
                        client_F = online[friend_id][0]
                        client_F.send(f"FRIEND_R|{user_id}".encode())
                        client.send("REQUESTED".encode())
                    else:
                        off_row = db.fetchone("SELECT offline FROM users WHERE id = ?", (friend_id,))
                        offline_old = off_row[0] if off_row else ""
                        if f"FRIEND_R|{user_id}" not in offline_old:
                            new_offline = offline_old + f"FRIEND_R|{user_id}\n"
                            db.execute("UPDATE users SET offline = ? WHERE id = ?", (new_offline, friend_id))
                            client.send("REQUESTED".encode())
                        else:
                            client.send("INVALID".encode())
                else:
                    client.send("INVALID".encode())

        elif parts[0] == "FRIEND_A":
            idU = int(parts[1])
            idF = int(parts[2])
            answer = parts[3]

            nameU = db.fetchone("SELECT name FROM users WHERE id = ?", (idU,))[0]
            nameF = db.fetchone("SELECT name FROM users WHERE id = ?", (idF,))[0]

            if answer == "Y":
                # Add each other as friends
                row_u = db.fetchone("SELECT friends FROM users WHERE id = ?", (idU,))
                friends_u = json.loads(row_u[0]) if row_u and row_u[0] else []
                friends_u.insert(0, [nameF, [idF]])
                db.execute("UPDATE users SET friends = ? WHERE id = ?", (json.dumps(friends_u), idU))

                row_f = db.fetchone("SELECT friends FROM users WHERE id = ?", (idF,))
                friends_f = json.loads(row_f[0]) if row_f and row_f[0] else []
                friends_f.insert(0, [nameU, [idU]])
                db.execute("UPDATE users SET friends = ? WHERE id = ?", (json.dumps(friends_f), idF))

                if idF not in online:
                    off_row = db.fetchone("SELECT offline FROM users WHERE id = ?", (idF,))
                    offline_old = off_row[0] if off_row else ""
                    new_offline = offline_old + f"ADDED|{idU}\n"
                    db.execute("UPDATE users SET offline = ? WHERE id = ?", (new_offline, idF))
                else:
                    client_F = online[idF][0]
                    client_F.send(f"ADDED|{idU}".encode())

                client.send(f"ADDED|{idF}".encode())

                # Create a private chat between them
                db.execute(
                    "INSERT INTO chats(list, text) VALUES (?, ?)",
                    (json.dumps([idU, idF]), "")
                )

            else:
                # Deny request
                if idF not in online:
                    off_row = db.fetchone("SELECT offline FROM users WHERE id = ?", (idF,))
                    offline_old = off_row[0] if off_row else ""
                    new_offline = offline_old + f"DENIED|{idU}\n"
                    db.execute("UPDATE users SET offline = ? WHERE id = ?", (new_offline, idF))
                else:
                    client_F = online[idF][0]
                    client_F.send(f"DENIED|{idU}".encode())

        elif parts[0] == "CALL":
            lst = json.loads(parts[1])
            caller_id = int(parts[2])

            # If caller is in another room, remove them
            for room_key, members in list(rooms.items()):
                if caller_id in members:
                    members.remove(caller_id)
                    if not members:
                        rooms.pop(room_key)
                    break

            # Enter or create voice chat room
            room_key = json.dumps(lst)
            if room_key not in rooms:
                rooms[room_key] = [caller_id]
                for pid in lst:
                    if pid in online and pid != caller_id:
                        x = lst.copy()
                        x.remove(pid)
                        online[pid][0].send(f"CALLING|{x}".encode())
            else:
                rooms[room_key].append(caller_id)

            # Notify all in room
            for pid in rooms[room_key]:
                online[pid][0].send(f"VC_enter|{caller_id} entered the voice chat".encode())

    client.close()

def sendall(lst, text):
    for i in lst:
        print(f"sending to {i}...")
        online[int(i)][0].send(text.encode())

# Start server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 9999))
server.listen()

print("Server running...")
while True:
    client, addr = server.accept()
    print(f"{addr} Connected")
    # Pass dummy third arg; SQLiteHelper is global
    threading.Thread(target=handle_client, args=(client, addr, None), daemon=True).start()
