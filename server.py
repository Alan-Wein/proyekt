import socket
import threading
import json
import time
import datetime
import base64
from collections import Counter
from SQL import SQLiteHelper


# --- ROBUST SOCKET FRAMING ---
def send_msg(sock, msg):
    try:
        encoded = msg.encode('utf-8')
        header = f"{len(encoded):<16}".encode('utf-8')
        sock.sendall(header + encoded)
    except:
        pass


def recv_msg(sock):
    try:
        header = sock.recv(16)
        if not header: return ""
        length = int(header.decode('utf-8').strip())
        data = b""
        while len(data) < length:
            chunk = sock.recv(min(4096, length - len(data)))
            if not chunk: break
            data += chunk
        return data.decode('utf-8')
    except:
        return ""


# -----------------------------

db = SQLiteHelper("users.db", check_same_thread=False)

db.execute("""
           CREATE TABLE IF NOT EXISTS users
           (
               email
               TEXT,
               name
               TEXT,
               password
               TEXT,
               id
               INTEGER,
               friends
               TEXT,
               offline
               TEXT,
               settings
               TEXT
           )
           """)
db.execute("""
           CREATE TABLE IF NOT EXISTS chats
           (
               list
               TEXT,
               text
               TEXT
           )
           """)

online = {}

# Encryption settings
ENCRYPTION_KEY = "MySecretChatKey123"


def encrypt_text(text):
    if not text: return ""
    encrypted = [chr(ord(c) ^ ord(ENCRYPTION_KEY[i % len(ENCRYPTION_KEY)])) for i, c in enumerate(text)]
    return base64.b64encode("".join(encrypted).encode('utf-8')).decode('utf-8')


def decrypt_text(text):
    if not text: return ""
    try:
        decoded = base64.b64decode(text.encode('utf-8')).decode('utf-8')
        decrypted = [chr(ord(c) ^ ord(ENCRYPTION_KEY[i % len(ENCRYPTION_KEY)])) for i, c in enumerate(decoded)]
        return "".join(decrypted)
    except:
        return text


# Voice Chat UDP Variables
udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_server.bind(("0.0.0.0", 9998))

vc_rooms = {}
user_udp = {}
udp_to_user = {}


def udp_listener():
    while True:
        try:
            data, addr = udp_server.recvfrom(4096)
            if data.startswith(b"REG|"):
                user_id = int(data.split(b"|")[1])
                user_udp[user_id] = addr
                udp_to_user[addr] = user_id
            else:
                user_id = udp_to_user.get(addr)
                if user_id is not None:
                    for room_key, members in vc_rooms.items():
                        if user_id in members:
                            for member in members:
                                if member != user_id and member in user_udp:
                                    udp_server.sendto(data, user_udp[member])
                            break
        except Exception as e:
            print("UDP Error:", e)


threading.Thread(target=udp_listener, daemon=True).start()


def find_key_dict(dct, value):
    for key, val in dct.items():
        if val == value:
            return key


def create_user(email, name, password):
    user_id = db.count("users")
    empty_list = []
    default_stgs = json.dumps({"noise": 0, "keybind": ""})
    db.execute(
        "INSERT INTO users(email, name, password, id, friends, offline, settings) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (email, name, password, user_id, json.dumps(empty_list), "", default_stgs)
    )
    return user_id


def verify_user(email, name, password):
    id1 = db.fetchone("SELECT id FROM users WHERE email = ?", (email,))
    if not id1: return None
    id2 = db.fetchone("SELECT id FROM users WHERE name = ? AND password = ?", (name, password))
    if not id2 or id1[0] != id2[0]: return -1
    else:
        return id1[0]


def update_vc_participants(room_key):
    time.sleep(0.05)
    if room_key not in vc_rooms: return
    members = vc_rooms[room_key]
    names = []
    for uid in members:
        row = db.fetchone("SELECT name FROM users WHERE id = ?", (uid,))
        names.append(row[0] if row else str(uid))
    for uid in members:
        if uid in online:
            send_msg(online[uid][0], f"VC_UPDATE|{json.dumps(names)}")


def handle_client(client, addr, _):
    while True:
        data = recv_msg(client)
        if not data or data == "EXIT":
            print(f"{addr} Disconnected")
            key = find_key_dict(online, (client, addr))
            if key is not None:
                online.pop(key)

            empty_rooms = []
            for room_key, members in vc_rooms.items():
                if key in members:
                    members.remove(key)
                    update_vc_participants(room_key)
                    if not members:
                        empty_rooms.append(room_key)
            for r in empty_rooms:
                del vc_rooms[r]

            send_msg(client, "EXIT")
            try:
                client.close()
            except:
                pass
            break

        if data == "CLEAR":
            db.execute("DELETE FROM users")
            db.execute("DELETE FROM chats")
            continue

        parts = data.split("|")

        if parts[0] == "OFFLINE" or parts[0] == "DONE":
            user_id = int(parts[1])
            if parts[0] == "OFFLINE":
                online[user_id] = (client, addr)

            offline_msg = db.fetchone("SELECT offline FROM users WHERE id = ?", (user_id,))
            offline_text = offline_msg[0] if offline_msg else ""
            if offline_text:
                first_line = offline_text.split("\n", 1)[0]
                if first_line:
                    send_msg(client, first_line)
                remaining = offline_text[len(first_line) + 1:] if "\n" in offline_text else ""
                db.execute("UPDATE users SET offline = ? WHERE id = ?", (remaining, user_id))

        elif parts[0] == "LOGIN":
            email, name, password_hash = parts[1], parts[2], parts[3]
            result = verify_user(email, name, password_hash)
            if result is None:
                new_id = create_user(email, name, password_hash)
                stgs_json = json.dumps({"noise": 0, "keybind": ""})
                send_msg(client, f"NEW|{new_id}|{stgs_json}")
            elif result == -1:
                send_msg(client, "NO")
            else:
                if result in online:
                    send_msg(client, "ONLINE")
                else:
                    settings_row = db.fetchone("SELECT settings FROM users WHERE id = ?", (result,))
                    stgs_json = settings_row[0] if settings_row and settings_row[0] else '{"noise": 0, "keybind": ""}'
                    send_msg(client, f"OK|{result}|{stgs_json}")

        elif parts[0] == "UPDATE_SETTINGS":
            user_id = int(parts[1])
            stgs_json = parts[2]
            db.execute("UPDATE users SET settings = ? WHERE id = ?", (stgs_json, user_id))

        elif parts[0] == "RESET_PASS":
            email = parts[1]
            old_pass = parts[2]
            new_pass = parts[3]
            row = db.fetchone("SELECT id FROM users WHERE email = ? AND password = ?", (email, old_pass))
            if row:
                db.execute("UPDATE users SET password = ? WHERE email = ?", (new_pass, email))
                send_msg(client, "RESET_OK")
            else:
                send_msg(client, "RESET_FAIL")

        elif parts[0] == "CHAT_START":
            f_list = json.loads(parts[1])
            rows = db.fetchall("SELECT list FROM chats")
            text = "HOW????"
            real_list = json.dumps(f_list)
            for row in rows:
                l = row[0]
                if Counter(f_list) == Counter(json.loads(l)):
                    chat_text = db.fetchone("SELECT text FROM chats WHERE list = ?", (l,))
                    decrypted_text = decrypt_text(chat_text[0]) if chat_text else ""
                    text = l + ":\n" + decrypted_text
                    real_list = l
                    break
            call_status = "ON" if real_list in vc_rooms else "OFF"
            send_msg(client, f"CHAT_START|{real_list}|{call_status}|{text}")

        elif parts[0] == "FILE":
            sender_id = parts[1]
            lst = json.loads(parts[2])
            filename = parts[3]
            b64_data = parts[4]

            name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (sender_id,))
            sender_name = name_row[0] if name_row else "Unknown"

            now = datetime.datetime.now()
            date_label = now.strftime("%A, %B %d, %Y")
            date_separator = f"--- {date_label} ---"
            timestamp = now.strftime("%H:%M")

            current = db.fetchone("SELECT text FROM chats WHERE list = ?", (json.dumps(lst),))
            current_text = decrypt_text(current[0]) if current else ""

            if date_separator not in current_text:
                prefix = "\n" if current_text != "" else ""
                current_text += f"{prefix}\n      {date_separator}\n"

            # Saving the file encoded safely in the db text payload
            formatted_message = f"{sender_name}> <FILE::{filename}::{b64_data}> [{timestamp}]"
            new_text = current_text + "\n" + formatted_message
            db.execute("UPDATE chats SET text = ? WHERE list = ?", (encrypt_text(new_text), json.dumps(lst)))

            for uid in lst:
                if uid in online:
                    # Notify them so their client pulls down the refreshed chat (with the new file embedded)
                    send_msg(online[uid][0], f"CHAT|{sender_id}|{json.dumps(lst)}")

        elif parts[0] == "CHAT":
            sender_id = parts[1]
            lst = json.loads(parts[2])
            message = parts[3]

            name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (sender_id,))
            sender_name = name_row[0] if name_row else "Unknown"

            now = datetime.datetime.now()
            date_label = now.strftime("%A, %B %d, %Y")
            date_separator = f"--- {date_label} ---"
            timestamp = now.strftime("%H:%M")

            current = db.fetchone("SELECT text FROM chats WHERE list = ?", (json.dumps(lst),))
            current_text = decrypt_text(current[0]) if current else ""

            if date_separator not in current_text:
                prefix = "\n" if current_text != "" else ""
                current_text += f"{prefix}\n      {date_separator}\n"

            formatted_message = f"{sender_name}> {message} [{timestamp}]"
            new_text = current_text + "\n" + formatted_message
            db.execute("UPDATE chats SET text = ? WHERE list = ?", (encrypt_text(new_text), json.dumps(lst)))

            for uid in lst:
                if uid in online:
                    send_msg(online[uid][0], f"CHAT|{sender_id}|{json.dumps(lst)}")

        elif parts[0] == "GROUP":
            lst = json.loads(parts[1])
            group_name = parts[2]
            db.execute("INSERT INTO chats(list, text) VALUES (?, ?)", (json.dumps(lst), encrypt_text("")))

            for user_id in lst:
                fake_lst = lst.copy()
                fake_lst.remove(user_id)
                row = db.fetchone("SELECT friends FROM users WHERE id = ?", (user_id,))
                friends = json.loads(row[0]) if row and row[0] else []
                friends.append([group_name, fake_lst])
                db.execute("UPDATE users SET friends = ? WHERE id = ?", (json.dumps(friends), user_id))

                if user_id not in online:
                    off_row = db.fetchone("SELECT offline FROM users WHERE id = ?", (user_id,))
                    offline_old = off_row[0] if off_row else ""
                    new_offline = offline_old + f"ADDED|{group_name}\n"
                    db.execute("UPDATE users SET offline = ? WHERE id = ?", (new_offline, user_id))
                else:
                    send_msg(online[user_id][0], f"ADDED|{group_name}")

        elif parts[0] == "CMD":
            user_id = int(parts[1])
            cmd = parts[2]

            if cmd == "list":
                row = db.fetchone("SELECT friends FROM users WHERE id = ?", (user_id,))
                friends_list = json.loads(row[0]) if row and row[0] else []
                send_msg(client, f"FRIENDS|{json.dumps(friends_list)}")

            elif cmd == "online":
                send_msg(client, f"ONLINE|{online}")

            elif cmd == "me":
                name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (user_id,))
                user_name = name_row[0] if name_row else ""
                send_msg(client, f"ME|{user_id}:{addr}|{user_name}")

            elif cmd.startswith("add "):
                friend_str = cmd[4:].strip()
                if not friend_str.isdigit():
                    send_msg(client, "INVALID")
                    continue
                friend_id = int(friend_str)

                max_id = db.count("users")
                row = db.fetchone("SELECT friends FROM users WHERE id = ?", (user_id,))
                current_friends = json.loads(row[0]) if row and row[0] else []

                if friend_id < max_id and friend_id not in current_friends and friend_id != user_id:
                    if friend_id in online:
                        send_msg(online[friend_id][0], f"FRIEND_R|{user_id}")
                        send_msg(client, "REQUESTED")
                    else:
                        off_row = db.fetchone("SELECT offline FROM users WHERE id = ?", (friend_id,))
                        offline_old = off_row[0] if off_row else ""
                        if f"FRIEND_R|{user_id}" not in offline_old:
                            new_offline = offline_old + f"FRIEND_R|{user_id}\n"
                            db.execute("UPDATE users SET offline = ? WHERE id = ?", (new_offline, friend_id))
                            send_msg(client, "REQUESTED")
                        else:
                            send_msg(client, "INVALID")
                else:
                    send_msg(client, "INVALID")

        elif parts[0] == "FRIEND_A":
            idU = int(parts[1])
            idF = int(parts[2])
            answer = parts[3]

            nameU = db.fetchone("SELECT name FROM users WHERE id = ?", (idU,))[0]
            nameF = db.fetchone("SELECT name FROM users WHERE id = ?", (idF,))[0]

            if answer == "Y":
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
                    send_msg(online[idF][0], f"ADDED|{idU}")

                send_msg(client, f"ADDED|{idF}")
                db.execute("INSERT INTO chats(list, text) VALUES (?, ?)", (json.dumps([idU, idF]), encrypt_text("")))

            else:
                if idF not in online:
                    off_row = db.fetchone("SELECT offline FROM users WHERE id = ?", (idF,))
                    offline_old = off_row[0] if off_row else ""
                    new_offline = offline_old + f"DENIED|{idU}\n"
                    db.execute("UPDATE users SET offline = ? WHERE id = ?", (new_offline, idF))
                else:
                    send_msg(online[idF][0], f"DENIED|{idU}")

        elif parts[0] == "CALL_INIT":
            room_key = parts[1]
            caller_id = int(parts[2])
            name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (caller_id,))
            caller_name = name_row[0] if name_row else str(caller_id)

            is_new_call = False
            if room_key not in vc_rooms:
                vc_rooms[room_key] = [caller_id]
                is_new_call = True
            elif caller_id not in vc_rooms[room_key]:
                vc_rooms[room_key].append(caller_id)

            lst = json.loads(room_key)

            timestamp = datetime.datetime.now().strftime("%H:%M")
            if is_new_call:
                call_start_msg = f"System> \U0001f4de Voice call started by {caller_name} [{timestamp}]"
                current = db.fetchone("SELECT text FROM chats WHERE list = ?", (room_key,))
                current_text = decrypt_text(current[0]) if current else ""
                new_text = current_text + "\n" + call_start_msg
                db.execute("UPDATE chats SET text = ? WHERE list = ?", (encrypt_text(new_text), room_key))

                for uid in lst:
                    if uid in online:
                        send_msg(online[uid][0], f"CALL_STATE|{room_key}|ON")
                        time.sleep(0.05)
                        send_msg(online[uid][0], f"CHAT|server|{room_key}")
                        if uid != caller_id:
                            time.sleep(0.05)
                            send_msg(online[uid][0], f"CALLING|{room_key}|{caller_id}|{caller_name}")
            else:
                for uid in vc_rooms[room_key]:
                    if uid != caller_id and uid in online:
                        send_msg(online[uid][0], f"VC_enter|{caller_name} joined the call. [{timestamp}]")
            update_vc_participants(room_key)

        elif parts[0] == "CALL_ACCEPT":
            room_key = parts[1]
            accepter_id = int(parts[2])

            if room_key in vc_rooms:
                if accepter_id not in vc_rooms[room_key]:
                    vc_rooms[room_key].append(accepter_id)

                name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (accepter_id,))
                accepter_name = name_row[0] if name_row else str(accepter_id)
                timestamp = datetime.datetime.now().strftime("%H:%M")

                for uid in vc_rooms[room_key]:
                    if uid in online:
                        send_msg(online[uid][0], f"VC_enter|{accepter_name} joined the call. [{timestamp}]")
                update_vc_participants(room_key)

        elif parts[0] == "CALL_LEAVE":
            leaver_id = int(parts[1])
            name_row = db.fetchone("SELECT name FROM users WHERE id = ?", (leaver_id,))
            leaver_name = name_row[0] if name_row else str(leaver_id)
            timestamp = datetime.datetime.now().strftime("%H:%M")

            empty_rooms = []
            for room_key, members in vc_rooms.items():
                if leaver_id in members:
                    members.remove(leaver_id)
                    for uid in members:
                        if uid in online:
                            send_msg(online[uid][0], f"VC_leave|{leaver_name} left the call. [{timestamp}]")
                    update_vc_participants(room_key)
                    if not members:
                        empty_rooms.append(room_key)

            for r in empty_rooms:
                del vc_rooms[r]
                call_end_msg = f"System> \U0001f6d1 Voice call ended [{timestamp}]"
                current = db.fetchone("SELECT text FROM chats WHERE list = ?", (r,))
                current_text = decrypt_text(current[0]) if current else ""
                new_text = current_text + "\n" + call_end_msg
                db.execute("UPDATE chats SET text = ? WHERE list = ?", (encrypt_text(new_text), r))

                lst = json.loads(r)
                for uid in lst:
                    if uid in online:
                        send_msg(online[uid][0], f"CALL_STATE|{r}|OFF")
                        time.sleep(0.05)
                        send_msg(online[uid][0], f"CHAT|server|{r}")

    try:
        client.close()
    except:
        pass


# Start server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 9999))
server.listen()

print("Server running...")
while True:
    client, addr = server.accept()
    print(f"{addr} Connected")
    threading.Thread(target=handle_client, args=(client, addr, None), daemon=True).start()
