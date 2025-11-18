import socket, threading, sqlite3, json

conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
    email TEXT,
    name TEXT,
    password TEXT,
    id INTEGER,
    friends TEXT
)
""")
conn.commit()
online = {}
def find_key_dict(dict, value):
    for key, value_ in dict.items():
        if value_ == value:
            return key

def create_user(email, name, password):
    c.execute("SELECT COUNT(*) FROM users")
    id = c.fetchone()[0]
    lst = []

    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",(email, name, password, id, json.dumps(lst)))
    conn.commit()
    return id

def verify_user(email, name, password):
    c.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if not row: return None  # no email => new user

    c.execute("SELECT id FROM users WHERE name=? AND password=?", (name, password))
    row = c.fetchone()
    return row[0] if row else -1  # -1 means wrong password

def handle_client(client,addr):

    while True:
        data = client.recv(2048).decode()
        if not data or data == "EXIT":
            print(addr.__str__()+" Disconnected")
            online.pop(find_key_dict(online, (client,addr)))
            client.send("EXIT".encode())
            client.close()
            break

        if data == "CLEAR":
            c.execute("DELETE FROM users")
            conn.commit()
            print("Data cleared")
            continue


        parts = data.split("|")

        if parts[0] == "LOGIN":
            email, name, password = parts[1], parts[2], parts[3]

            # check user
            id = verify_user(email, name, password)

            if id is None:
                id = create_user(email, name, password)
                client.send(f"NEW|{id}".encode())
                online[id]=(client,addr)
            elif id == -1:
                client.send("NO".encode())
            else:
                client.send(f"OK|{id}".encode())
                online[id] = (client, addr)

        elif parts[0] == "CMD":
            id = int(parts[1])
            cmd = parts[2]

            # handle chat commands
            if cmd == "list":
                c.execute("SELECT friends FROM users WHERE id=?", (id,))
                lst = json.loads(c.fetchone()[0])
                client.send(f"FRIENDS|{lst}".encode())

            elif cmd == "online":
                client.send(f"ONLINE|{online}".encode())

            elif cmd == "me":
                client.send(f"ME|{addr}".encode())

            elif cmd.startswith("add "):
                value = cmd[4:].strip()
                c.execute("SELECT COUNT(*) FROM users")
                max_id = c.fetchone()[0]

                c.execute("SELECT friends FROM users WHERE id=?", (id,))
                lst = json.loads(c.fetchone()[0])

                if value.isdigit() and int(value) < max_id and int(value) not in lst and int(value) != id:
                    lst.append(int(value))
                    c.execute("UPDATE users SET friends=? WHERE id=?",
                              (json.dumps(lst), id))
                    conn.commit()
                    client.send("ADDED".encode())
                else:
                    client.send("INVALID".encode())
            else:
                client.send("INVALID".encode())

    client.close()


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 9999))
server.listen()

print("Server running...")
while True:
    client, addr = server.accept()
    print(addr.__str__()+" Connected")
    threading.Thread(target=handle_client, args=(client,addr), daemon=True).start()

