import json, socket, threading, GUI, keyboard

in_chat=None
s = socket.socket()
s.connect(("127.0.0.1", 9999))
f_btns=[]
friends=[]##friends[i]=(id,name)
gui=GUI.GUI()
def btn_create(list,id):
    for b in list:
        friends=b.hidden
        friends.append(int(id))
        b.configure(command=lambda friends=friends: button_click(friends),)

def button_click(friends):
    s.send(f"CHAT_START|{json.dumps(friends)}".encode())


def closed(root):
    s.send("EXIT".encode())
    root.destroy()

def enter_pressed(entrybox,textbox,id,name):

    text=entrybox.get()
    is_down= textbox.yview()[1] == 1.0
    gui.enter_pressed(entrybox,textbox,name)
    if is_down:
        gui.down(textbox)
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
        gui.popup("Group name not entered")
        root.attributes('-topmost', True)
        return
    lst=[int(id)]
    for cb in checkboxes:
        if cb.var.get()==1:
            # print(cb.var.get())
            lst.append(cb.hidden[0])
    if len(lst)<3:
        root.attributes('-topmost', True)
        gui.popup("Not enough checkboxes have been pressed")
        root.attributes('-topmost', True)
        return
    s.send(f"GROUP|{lst}|{name}".encode())
    root.destroy()

def group(id):
    root=gui.root("Group Create","500x500",False)
    root.attributes('-topmost', True)
    BOXES_PER_ROW=3

    entrybox=gui.entrybox(root)
    entrybox.grid(column=0,row=1,columnspan=BOXES_PER_ROW)
    lst=[]
    for i in range(len(friends)):
        if len(friends[i][1])<3:
            lst.append(friends[i])
    checkboxes=[]
    for i in range(len(lst)):
        row = i // BOXES_PER_ROW
        col = i % BOXES_PER_ROW
        checkbox=gui.checkbox(root,lst[i][0],lst[i][1])
        checkbox.grid(row=row+2, column=col, padx=10, pady=10)
        checkboxes.append(checkbox)
    buttonCreate = gui.button(root, "Create Group", lambda: pressed(id,root,entrybox.get(),checkboxes))
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
        gui.popup("Name or password incorrect. Try again")
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
    root = gui.root("Login","400x320",False)

    labelE=gui.label(root, text="Email:").pack(anchor="w", padx=20, pady=(15, 0))
    entryE=gui.entrybox(root)
    entryE.pack(fill="x", padx=20)


    labelU=gui.label(root, text="Username:").pack(anchor="w", padx=20, pady=(10, 0))
    entryU=gui.entrybox(root)
    entryU.pack(fill="x", padx=20)

    labelP=gui.label(root, text="Password:").pack(anchor="w", padx=20, pady=(10, 0))
    entryP=gui.entrybox(root,True)
    entryP.pack(fill="x", padx=20)

    button=gui.button(root, text="Log In",comand=lambda :login(root,entryE,entryU,entryP))
    button.pack(pady=20)

    root.protocol("WM_DELETE_WINDOW", lambda: closed(root))
    root.mainloop()


def start(id):
    global friends

    root=gui.root("hi","1000x600",True)
##### TOOLBAR ######
    toolbar = gui.frame(root, bd=1, relief="raised")
    toolbar.grid(row=0, column=0, sticky="ew")

    call=gui.button(toolbar, text="Start call",comand=lambda :begin())
    call.configure(state="disabled")
    call.grid(row=0,column=1,padx=5, pady=5)

    btn_quit = gui.button(toolbar, text="Quit", comand=lambda :closed(root))
    btn_quit.grid(row=0, column=0, padx=5, pady=5)
##### LEFT SIDE #####


    textbox=gui.textbox(root)
    textbox.grid(row=1, column=0, padx=10, pady=1, rowspan=5)

    entry=gui.entrybox(root)
    entry.configure(width=root.winfo_screenwidth())
    entry.grid(row=10, column=0, padx=10, pady=1, rowspan=1)
    s.send(f"CMD|{id}|me".encode())
    reply=s.recv(2048).decode().split("|")
    name=reply[2]
    keyboard.add_hotkey('enter', lambda :enter_pressed(entry,textbox,id,name))


######  RIGHT SIDE #####
    buttonGroup = gui.button(root, "Create Group", comand=lambda: group(id))
    buttonGroup.grid(row=1, column=1, padx=10, pady=1)

    entryADD=gui.entrybox(root)
    entryADD.grid(row=3,column=1,padx=10, pady=1)

    buttonADD=gui.button(root,"Add Friend(input id)",comand=lambda :addFriend(id,entryADD))
    buttonADD.grid(row=2,column=1,padx=10, pady=1)


    labelF=gui.label(root,"Friend List")
    labelF.grid(row=4, column=1, padx=10, pady=5)
    s.send(f"CMD|{id}|list".encode())
    friends = json.loads(s.recv(2048).decode().split("|")[1])
    f_btns=gui.scrollbar(root,5,1,friends)
    btn_create(f_btns,id)





    s.send(f"OFFLINE|{id}".encode())
    threading.Thread(target=listen, args=(s,root,textbox,id,call), daemon=True).start()

    root.protocol("WM_DELETE_WINDOW", lambda: closed(root))
    root.mainloop()
def addFriend(id,entryADD):
    s.send(f"CMD|{id}|add {entryADD.get()}".encode())
    entryADD.delete(0,"end")



def listen(s,root,textbox,id,call):
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
            answer = gui.question(f"Do you want to be friends with {idf}?")
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
            gui.popup(f"{parts[1]} added!")
            s.send(f"CMD|{id}|list".encode())
            friends = json.loads(s.recv(2048).decode().split("|")[1])
            f_btns=gui.scrollbar(root, 5, 1, friends)
            btn_create(f_btns,id)
            s.send(f"DONE|{id}".encode())
            continue

        elif parts[0]=="CHAT_START":
            gui.textClear(textbox)
            in_chat=parts[1]
            text = parts[2]

            gui.type(textbox,text+'\n')
            if is_down:
                gui.down(textbox)

            call.configure(state="normal",command=lambda :calling(id,in_chat))

            continue
        elif parts[0]=="CHAT":
            friend=parts[1]
            list=parts[2]
            if in_chat==list:
                s.send(f"CHAT_START|{list}".encode())
            continue

        elif parts[0] == "CALLING":
            lst=parts[1]
            answer = gui.question(f"Do you want to enter a call with {lst}?")
            if answer:
                calling(id,lst)
            continue

        if parts[0] == "VC_enter":
            text=parts[1]
            gui.type(textbox,f"{text} \n")
            continue



        elif parts[0]=="DENIED":
            gui.popup(f"Friend {parts[1]} DENIED your request!")
            continue

        elif reply == "REQUESTED":
            gui.popup(f"Friend request sent!")
            continue

        elif reply == "INVALID":
            gui.popup("INVALIIIIID")
            continue

        else:
            text="??????????????"

        gui.type(textbox,"Server> "+text+'\n')
        if is_down:
            gui.down(textbox)

def calling(id,lst):
    root=gui.root("call","500x500",False)
    textbox=gui.textbox(root)
    textbox.pack(side="top",fill="x")
    gui.type(textbox,f"id: {id} \n")
    gui.type(textbox,f"lst: {lst} \n")
    print(lst)
    s.send(f"CALL|{lst}|{id}".encode())
    root.mainloop()



    # while True:
    #     reply = s.recv(2048).decode()
    #     parts = reply.split("|")
    #
    #     if parts[0]=="VC_enter":
    #         text=parts[1]
    #         gui.type(textbox,f"{text} \n")
    #         print("here")


if __name__=="__main__":
    begin()
