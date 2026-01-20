import socket, threading, sqlite3, json,time
from collections import Counter


conn = sqlite3.connect("users.db", check_same_thread=False)
main_c = conn.cursor()

main_c.execute("""
CREATE TABLE IF NOT EXISTS users(
    email TEXT,
    name TEXT,
    password TEXT,
    id INTEGER,
    friends TEXT,
    offline TEXT
)
""")

main_c.execute("""
CREATE TABLE IF NOT EXISTS chats(
    list TEXT,
    text TEXT
)
""")
conn.commit()
online = {}
def find_key_dict(dict, value):
    for key, value_ in dict.items():
        if value_ == value:
            return key


def create_user(email, name, password):
    main_c.execute("SELECT COUNT(*) FROM users")
    id = main_c.fetchone()[0]
    lst = []

    main_c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",(email, name, password, id, json.dumps(lst),""))
    conn.commit()
    return id

def verify_user(email, name, password):
    main_c.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = main_c.fetchone()
    if not row: return None  # no email => new user

    main_c.execute("SELECT id FROM users WHERE name=? AND password=?", (name, password))
    row = main_c.fetchone()
    return row[0] if row else -1  # -1 means wrong password

def Offline(id):
    main_c.execute("SELECT offline FROM users WHERE id = ?", (id,))
    offline = main_c.fetchone()[0]
    if offline != "":
        lines = offline.split("\n")
        line=lines[0]
        if line != "":
            client.send(line.encode())
        main_c.execute("UPDATE users SET offline=? WHERE id=?", (offline[len(line)+1:], id))
    conn.commit()


def handle_client(client,addr,c):

    while True:
        data = client.recv(2048).decode()
        if not data or data == "EXIT":
            print(addr.__str__()+" Disconnected")
            key=find_key_dict(online, (client,addr))
            if key!=None:
                online.pop(key)
            client.send("EXIT".encode())
            client.close()
            break

        if data == "CLEAR":
            c.execute("DELETE FROM users")
            c.execute("DELETE FROM chats")
            conn.commit()
            continue



        parts = data.split("|")
        if parts[0] == "OFFLINE":
            id=int(parts[1])
            Offline(id)
            online[id]=(client,addr)

        if parts[0] == "DONE":
            id=int(parts[1])
            Offline(id)

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

        elif parts[0] == "CHAT_START":
            f_list = json.loads(parts[1])
            c.execute("SELECT list FROM chats")
            list = c.fetchall()
            text="HOW????"
            real_list=f_list
            for l in list:
                l=l[0]
                if Counter(f_list) == Counter(json.loads(l)):
                    c.execute("SELECT text FROM chats WHERE list=?",(l,))
                    text=l+":\n"+c.fetchone()[0]
                    real_list=l
                    break
            client.send(f"CHAT_START|{real_list}|{text}".encode())

        elif parts[0] == "CHAT":
            id=parts[1]
            list=json.loads(parts[2])
            c.execute("SELECT name FROM users WHERE id=?", (id,))
            upload=c.fetchone()[0]+"> "+parts[3]
            c.execute("SELECT text FROM chats WHERE list=?", (json.dumps(list),))
            text=c.fetchone()[0]
            text+="\n"
            c.execute("UPDATE chats SET text=? WHERE list=?", (text+upload, json.dumps(list)))
            conn.commit()
            for i in list:
                if str(i)!=id:
                    if i in online:
                        cF = online[i][0]
                        cF.send(f"CHAT|{id}|{list}".encode())

        elif parts[0] == "GROUP":
            lst=json.loads(parts[1])
            name=parts[2]
            c.execute("INSERT INTO chats VALUES (?, ?)", (json.dumps(lst), ""))

            for user in lst:
                print(user)
                user=int(user)
                c.execute("SELECT friends FROM users WHERE id=?", (user,))
                friends = json.loads(c.fetchone()[0])
                friends.append((name,lst))
                c.execute("UPDATE users SET friends=? WHERE id=?", (json.dumps(friends), user))

                if user not in online:
                    c.execute("SELECT offline FROM users WHERE id=?", (user,))
                    offline = c.fetchone()[0]
                    c.execute("UPDATE users SET offline=? WHERE id=?",
                              (offline + f"ADDED|{lst}\n", user))
                else:
                    cF = (online[user])[0]
                    cF.send(f"ADDED|{lst}".encode())



        elif parts[0] == "CMD":
            id = int(parts[1])
            cmd = parts[2]


            if cmd == "list":
                c.execute("SELECT friends FROM users WHERE id=?", (id,))
                lst_id = json.loads(c.fetchone()[0])
                lst_name=[]
                for i in lst_id:
                    if type(i)==type(1):
                        c.execute("SELECT name FROM users WHERE id=?", (i,))
                        name=c.fetchone()[0]
                    else:
                        name = i[0]
                    lst_name.insert(0,(i,name))##ID,NAME

                client.send(f"FRIENDS|{json.dumps(lst_name)}".encode())

            elif cmd == "online":
                client.send(f"ONLINE|{online}".encode())

            elif cmd == "me":
                c.execute("SELECT name FROM users WHERE id=?", (id,))
                name=c.fetchone()[0]
                client.send(f"ME|{id}:{addr}|{name}".encode())

            elif cmd.startswith("add "):
                value = cmd[4:].strip()
                if not value.isdigit():
                    client.send("INVALID".encode())
                    continue
                friend=int(value)
                c.execute("SELECT COUNT(*) FROM users")
                max_id = c.fetchone()[0]

                c.execute("SELECT friends FROM users WHERE id=?", (id,))
                lst = json.loads(c.fetchone()[0])
                if friend < max_id and friend not in lst and friend != id: #valid command
                    if friend in online.keys():
                        cF=online[friend][0]
                        cF.send(f"FRIEND_R|{id}".encode())#friend request
                        client.send("REQUESTED".encode())

                    else:               #offline
                        c.execute("SELECT offline FROM users WHERE id=?", (friend,))
                        offline = c.fetchone()[0]
                        if f"FRIEND_R|{id}" not in offline:
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
            answer=parts[3]
            if answer =="Y":
                c.execute("SELECT friends FROM users WHERE id=?", (idU,))#add idF to idU
                lst = json.loads(c.fetchone()[0])
                lst.insert(0, int(idF))
                c.execute("UPDATE users SET friends=? WHERE id=?", (json.dumps(lst), idU))
                c.execute("SELECT friends FROM users WHERE id=?", (idF,))#add idU to idF
                lst = json.loads(c.fetchone()[0])
                lst.insert(0, int(idU))
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
                    cF.send(f"ADDED|{idU}".encode())

                client.send(f"ADDED|{idF}".encode())

                c.execute("INSERT INTO chats VALUES (?, ?)",(json.dumps([idU,idF]), ""))

                conn.commit()

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
    threading.Thread(target=handle_client, args=(client,addr,conn.cursor()), daemon=True).start()
