import json, socket, threading, screen, keyboard

in_chat=None
s = socket.socket()
s.connect(("127.0.0.1", 9999))
f_btns=[]
friends=[]##friends[i]=(id,name)

def btn_create(list,id):
    for b in list:
        b.configure(command=lambda b=b: button_click(b.hidden,id),)

def button_click(friend,id):
    s.send(f"CHAT_START|{json.dumps([int(id),int(friend)])}".encode())


def closed(root):
    s.send("EXIT".encode())
    root.destroy()

def enter_pressed(entrybox,textbox,id,name):

    text=entrybox.get()
    is_down= textbox.yview()[1] == 1.0
    screen.enter_pressed(entrybox,textbox,name)
    if is_down:
        screen.down(textbox)
    if in_chat != None and text!="":
        s.send(f"CHAT|{id}|{in_chat}|{text}".encode())
    elif text=="/exit":
        s.send("EXIT".encode())
    elif text.startswith("/"):
        text=text[1:]
        s.send(f"CMD|{id}|{text}".encode())
def pressed(id,root,name,checkboxes):
    if name=="":
        root.attributes('-topmost', False)
        screen.popup("Group name not entered")
        root.attributes('-topmost', True)
        return
    lst=[]
    for cb in checkboxes:
        if cb.var.get()==1:
            print(cb.var.get())
            lst.append(cb.hidden)
    lst.append(int(id))
    s.send(f"GROUP|{lst}|{name}".encode())
    root.destroy()

def group(id):
    root=screen.root("Group Create","500x500",False)
    root.attributes('-topmost', True)
    BOXES_PER_ROW=3

    entrybox=screen.entrybox(root)
    entrybox.grid(column=0,row=1,columnspan=BOXES_PER_ROW)

    checkboxes=[]
    for i in range(len(friends)):
        row = i // BOXES_PER_ROW
        col = i % BOXES_PER_ROW
        checkbox=screen.checkbox(root,friends[i][1],friends[i][0])
        checkbox.grid(row=row+2, column=col, padx=10, pady=10)
        checkboxes.append(checkbox)
    buttonCreate = screen.button(root, "Create Group", lambda: pressed(id,root,entrybox.get(),checkboxes))
    buttonCreate.grid(row=0, column=0, columnspan=BOXES_PER_ROW, pady=10, padx=10)
    root.mainloop()









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

    root.protocol("WM_DELETE_WINDOW", lambda: closed(root))
    root.mainloop()


def start(id):
    global friends
    root=screen.root("hi","1000x600",True)
    textbox=screen.textbox(root)
    textbox.grid(row=1, column=0, padx=10, pady=1, rowspan=5)

    entryADD=screen.entrybox(root)
    entryADD.grid(row=3,column=1,padx=10, pady=1)
    buttonADD=screen.button(root,"Add Friend(input id)",comand=lambda :addFriend(id,entryADD))
    buttonADD.grid(row=2,column=1,padx=10, pady=1)


    labelF=screen.label(root,"Friend List")
    labelF.grid(row=4, column=1, padx=10, pady=5)
    s.send(f"CMD|{id}|list".encode())
    friends = json.loads(s.recv(2048).decode().split("|")[1])
    f_btns=screen.scrollbar(root,5,1,friends)
    btn_create(f_btns,id)

    buttonGroup = screen.button(root, "Create Group", comand=lambda: group(id))
    buttonGroup.grid(row=1, column=1, padx=10, pady=1)


    entry=screen.entrybox(root)
    entry.configure(width=root.winfo_screenwidth())
    entry.grid(row=10, column=0, padx=10, pady=1, rowspan=1)
    s.send(f"CMD|{id}|me".encode())
    reply=s.recv(2048).decode().split("|")
    name=reply[2]
    keyboard.add_hotkey('enter', lambda :enter_pressed(entry,textbox,id,name))


    s.send(f"OFFLINE|{id}".encode())
    threading.Thread(target=listen, args=(s,root,textbox,id), daemon=True).start()

    root.protocol("WM_DELETE_WINDOW", lambda: closed(root))
    root.mainloop()
def addFriend(id,entryADD):
    s.send(f"CMD|{id}|add {entryADD.get()}".encode())
    entryADD.delete(0,"end")



def listen(s,root,textbox,id):
    global friends
    global in_chat
    while True:
        is_down = textbox.yview()[1] == 1.0
        reply = s.recv(2048).decode()


        parts = reply.split("|")
        if reply == "EXIT":
            root.destroy()
            break
        if parts[0]=="FRIENDS":
            text="Friends list:"+ parts[1]

        elif parts[0]=="FRIEND_R":
            idf=parts[1]
            answer = screen.question(f"Do you want to be friends with {idf}?")
            if answer:
                text = "Y"
            else:
                text = "N"
            s.send(f"FRIEND_A|{id}|{idf}|{text}".encode())
            continue


        elif parts[0]=="ME":
            text="You are:"+ parts[1]

        elif parts[0]=="ONLINE":
            text="Online list:"+ parts[1]

        elif parts[0]=="ADDED":
            screen.popup(f"{parts[1]} added!")
            s.send(f"CMD|{id}|list".encode())
            friends = json.loads(s.recv(2048).decode().split("|")[1])
            f_btns=screen.scrollbar(root, 5, 1, friends)
            btn_create(f_btns,id)
            s.send(f"DONE|{id}".encode())
            continue
        elif parts[0]=="CHAT_START":
            screen.textClear(textbox)
            in_chat=parts[1]
            text = parts[2]

            screen.type(textbox,text+'\n')
            if is_down:
                screen.down(textbox)
            continue
        elif parts[0]=="CHAT":
            friend=parts[1]
            list=parts[2]
            if in_chat==list:
                s.send(f"CHAT_START|{json.dumps([int(id), int(friend)])}".encode())
            continue

        elif parts[0]=="DENIED":
            screen.popup(f"Friend {parts[1]} DENIED your request!")
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
        if is_down:
            screen.down(textbox)


if __name__=="__main__":
    begin()
