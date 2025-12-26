import json, socket, threading, screen, keyboard



s = socket.socket()
s.connect(("127.0.0.1", 9999))

def enter_pressed(entrybox,textbox,id):
    text=entrybox.get()
    screen.enter_pressed(entrybox,textbox)
    if text=="/exit":
        s.send("EXIT".encode())
    elif text.startswith("/"):
        text=text[1:]
        s.send(f"CMD|{id}|{text}".encode())


def login(root,entryE,entryU,entryP):

    email = entryE.get()
    name = entryU.get()
    password = entryP.get()

    if email == "e" and name == "e" and password == "e":
        s.send("EXIT".encode())
        root.destroy()
        return
    if email == "clear" and name == "e" and password == "e":
        s.send("CLEAR".encode())
        entryE.delete(0,"end")
        entryU.delete(0,"end")
        entryP.delete(0,"end")

        return
    else:
        s.send(f"LOGIN|{email}|{name}|{password}".encode())
    response = s.recv(2048).decode()

    if response == "NO":
        screen.popup("Name or password incorrect. Try again")
        entryE.delete(0,"end")
        entryU.delete(0,"end")
        entryP.delete(0,"end")
        return

    elif response.startswith("NEW"):
        id = response.split("|")[1]
        root.destroy()
        start(id)

    elif response.startswith("OK"):
        id = response.split("|")[1]
        root.destroy()
        start(id)


def begin():
    root = screen.root("Login","400x320",False)

    labelE=screen.label(root, text="Email:").pack(anchor="w", padx=20, pady=(15, 0))
    entryE=screen.entrybox(root)
    entryE.pack(fill="x", padx=20)


    labelU=screen.label(root, text="Username:").pack(anchor="w", padx=20, pady=(10, 0))
    entryU=screen.entrybox(root)
    entryU.pack(fill="x", padx=20)

    labelP=screen.label(root, text="Password:").pack(anchor="w", padx=20, pady=(10, 0))
    entryP=screen.entrybox(root,True)
    entryP.pack(fill="x", padx=20)

    button=screen.button(root, text="Log In",comand=lambda :login(root,entryE,entryU,entryP))
    button.pack(pady=20)

    root.mainloop()


def start(id):
    root=screen.root("hi","1000x600",True)
    textbox=screen.textbox(root)
    textbox.grid(row=1, column=0, padx=10, pady=1, rowspan=5)

    entryADD=screen.entrybox(root)
    entryADD.grid(row=2,column=1,padx=10, pady=1)
    buttonADD=screen.button(root,"Add Friend(input id)",comand=lambda :addFriend(id,entryADD))
    buttonADD.grid(row=1,column=1,padx=10, pady=1)

    labelF=screen.label(root,"Friend List")
    labelF.grid(row=3, column=1, padx=10, pady=5)
    s.send(f"CMD|{id}|list".encode())
    friends = json.loads(s.recv(2048).decode().split("|")[1])
    print(friends)
    scrollbar=screen.scrollbar(root,4,1,friends,textbox)
    entry=screen.entrybox(root)
    entry.configure(width=root.winfo_screenwidth())
    entry.grid(row=10, column=0, padx=10, pady=1, rowspan=1)
    keyboard.add_hotkey('enter', lambda :enter_pressed(entry,textbox,id))


    s.send(f"OFFLINE|{id}".encode())
    threading.Thread(target=listen, args=(s,root,textbox,id,scrollbar), daemon=True).start()


    root.mainloop()
def addFriend(id,entryADD):
    print(entryADD.get())
    s.send(f"CMD|{id}|add {entryADD.get()}".encode())
    entryADD.delete(0,"end")




def listen(s,root,textbox,id,scrollbar):
    while True:
        reply = s.recv(2048).decode()
        if reply == "EXIT":
            root.destroy()
            break
        if reply.startswith("FRIENDS"):
            text="Friends list:"+ reply.split("|")[1]

        elif reply.startswith("FRIEND_R"):
            print("works?")
            idf=reply.split("|")[1]
            answer=screen.question(f"Do you want to be friends with {idf}?")
            if answer: text="Y"
            else: text="N"
            s.send(f"FRIEND_A|{id}|{idf}|{text}".encode())


        elif reply.startswith("ME"):
            text="You are:"+ reply.split("|")[1]

        elif reply.startswith("ONLINE"):
            text="Online list:"+ reply.split("|")[1]

        elif reply.startswith("ADDED"):
            screen.popup(f"Friend {reply.split("|")[1]} added!")
            s.send(f"CMD|{id}|list".encode())
            friends = json.loads(s.recv(2048).decode().split("|")[1])
            scrollbar = screen.scrollbar(root, 4, 1, friends, textbox)
            continue

        elif reply.startswith("DENIED"):
            screen.popup(f"Friend {reply.split("|")[1]} DENIED your request!")
            continue
        elif reply == "REQUESTED":
            screen.popup(f"Friend request sent!")
            continue

        elif reply == "INVALID":
            screen.popup("INVALIIIIID")
            continue

        else:
            text="??????????????"

        screen.type(textbox,"Server> "+text+'\n')


if __name__=="__main__":
    begin()
