import socket, threading, sqlite3, json


conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
    email TEXT,
    name TEXT,
    password TEXT,
    id INTEGER,
    friends TEXT,
    offline TEXT
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

    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",(email, name, password, id, json.dumps(lst),""))
    conn.commit()
    return id

def verify_user(email, name, password):
    c.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if not row: return None  # no email => new user

    c.execute("SELECT id FROM users WHERE name=? AND password=?", (name, password))
    row = c.fetchone()
    return row[0] if row else -1  # -1 means wrong password

def Offline(id):
    print("back online")
    c.execute("SELECT offline FROM users WHERE id = ?", (id,))
    offline = c.fetchone()[0]
    print("offline:",offline)
    if offline != "":
        lines = offline.split("\n")
        for line in lines:
            if line != "":
                print("sending offline..")
                client.send(line.encode())
    print("UPDATING OFFLINE..")
    c.execute("UPDATE users SET offline=? WHERE id=?", ("", id))
    conn.commit()


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
        if parts[0] == "OFFLINE":
            id=int(parts[1])
            Offline(id)
            online[id]=(client,addr)

        elif parts[0] == "LOGIN":
            email, name, password = parts[1], parts[2], parts[3]


            id = verify_user(email, name, password)

            if id is None:
                id = create_user(email, name, password)
                client.send(f"NEW|{id}".encode())
                #
            elif id == -1:
                client.send("NO".encode())
            else:
                client.send(f"OK|{id}".encode())


        elif parts[0] == "CMD":
            id = int(parts[1])
            cmd = parts[2]


            if cmd == "list":
                c.execute("SELECT friends FROM users WHERE id=?", (id,))
                lst_id = json.loads(c.fetchone()[0])
                lst_name=[]
                for i in lst_id:
                    c.execute("SELECT name FROM users WHERE id=?", (i,))
                    lst_name.append(c.fetchone()[0])
                print(json.dumps(lst_name))

                client.send(f"FRIENDS|{json.dumps(lst_name)}".encode())

            elif cmd == "online":
                client.send(f"ONLINE|{online}".encode())

            elif cmd == "me":
                client.send(f"ME|{id}:{addr}".encode())

            elif cmd.startswith("add "):
                value = cmd[4:].strip()
                if not value.isdigit():
                    print("digit")
                    client.send("INVALID".encode())
                    continue
                friend=int(value)
                c.execute("SELECT COUNT(*) FROM users")
                max_id = c.fetchone()[0]

                c.execute("SELECT friends FROM users WHERE id=?", (id,))
                lst = json.loads(c.fetchone()[0])
                if friend < max_id and friend not in lst and friend != id: #valid command
                    print(f"keys: {online.keys()}")
                    if friend in online.keys():
                        print("is online(add)")
                        cF=online[friend][0]
                        cF.send(f"FRIEND_R|{id}".encode())#friend request
                        client.send("REQUESTED".encode())

                    else:               #offline
                        c.execute("SELECT offline FROM users WHERE id=?", (friend,))
                        offline = c.fetchone()[0]
                        print(f"offline(add1): {offline}")
                        if f"FRIEND_R|{id}" not in offline:
                            print(f"offline(add2): {offline}")
                            c.execute("UPDATE users SET offline=? WHERE id=?",
                                      (offline+f"FRIEND_R|{id}\n",friend))
                            client.send("REQUESTED".encode())
                        else:
                            client.send("INVALID".encode())
                else:
                    client.send("INVALID".encode())
            else:
                client.send("INVALID".encode())

        elif parts[0] == "FRIEND_A":
            idU=int(parts[1])
            idF=int(parts[2])
            print(online)
            print (idF)
            answer=parts[3]
            if answer =="Y":
                c.execute("SELECT friends FROM users WHERE id=?", (idU,))#add idF to idU
                lst = json.loads(c.fetchone()[0])
                lst.append(int(idF))
                c.execute("UPDATE users SET friends=? WHERE id=?",
                          (json.dumps(lst), idU))
                c.execute("SELECT friends FROM users WHERE id=?", (idF,))#add idU to idF
                lst = json.loads(c.fetchone()[0])
                lst.append(int(idU))
                c.execute("UPDATE users SET friends=? WHERE id=?",
                          (json.dumps(lst), idF))
                conn.commit()
                if idF not in online:
                    c.execute("SELECT offline FROM users WHERE id=?", (idF,))
                    offline = c.fetchone()[0]
                    c.execute("UPDATE users SET offline=? WHERE id=?",
                              (offline + f"ADDED|{idU}\n", idF))
                else:
                    cF = (online[idF])[0]
                    print(f"send added to {cF}")
                    cF.send(f"ADDED|{idU}".encode())

                print("send added  to client ans")
                client.send(f"ADDED|{idF}".encode())

            else:
                if idF not in online:
                    c.execute("SELECT offline FROM users WHERE id=?", (idF,))
                    offline = c.fetchone()[0]
                    c.execute("UPDATE users SET offline=? WHERE id=?",
                              (offline + f"DENIED|{idU}\n", idF))
                else:
                    cF = (online[idF])[0]
                    cF.send(f"DENIED|{idU}".encode())

    client.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 9999))
server.listen()

print("Server running...")
while True:
    client, addr = server.accept()
    print(addr.__str__()+" Connected")
    threading.Thread(target=handle_client, args=(client,addr), daemon=True).start()
