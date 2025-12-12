import socket
import threading
import time
import screen
import tkinter as tk
idF=-1
s = socket.socket()
s.connect(("127.0.0.1", 9999))
def login():

    email = input("Enter email: ")
    name = input("Enter name: ")
    password = input("Enter password: ")
    if email == "e" and name == "e" and password == "e":
        s.send("EXIT".encode())
        return
    if email == "clear" and name == "e" and password == "e":
        s.send("CLEAR".encode())
        login()
        return
    else:
        s.send(f"LOGIN|{email}|{name}|{password}".encode())
    response = s.recv(2048).decode()

    if response == "NO":
        print("Name or password incorrect")
        login()

    elif response.startswith("NEW"):
        id = response.split("|")[1]
        print("Hello for the first time!")
        start(id)
    elif response.startswith("OK"):
        id = response.split("|")[1]
        print("Welcome back!")
        start(id)

def start(id):
    root=screen.root("hi","1000x600",True)
    textbox=screen.textbox(root)
    textbox.grid(row=1, column=0, padx=10, pady=1, rowspan=5)
    label=screen.label(root,"Friend List")
    label.grid(row=0, column=1, padx=10, pady=5)

    s.send(f"CMD|{id}|list".encode())
    friends = s.recv(2048).decode().split("|")[1][1:-1].split(",")
    screen.scrollbar(root,2,1,friends,textbox)


    root.mainloop()
    # threading.Thread(target=listen, args=(s,), daemon=True).start()
    # talk(s,id)

def talk(s,id):
    global idF
    # while True:
    time.sleep(0.1)
    if idF!=-1:
        answer = input(f"id - {idF} requested friendship, answer Y/N: ")
        while answer != "Y" and answer != "N":
            answer = input("Wrong answer, try again: ")
        s.send(f"FRIEND_A|{id}|{idF}|{answer}".encode())
        idF=-1
    else:
        text = input("> ")

        if text == "exit":
            s.send("EXIT".encode())
            print("Goodbye")
            # break
        s.send(f"CMD|{id}|{text}".encode())


def listen(s):
    global idF
    while True:
        reply = s.recv(2048).decode()
        if reply == "EXIT":
            break
        if reply.startswith("FRIENDS"):
            print("Friends list:", reply.split("|")[1])

        elif reply.startswith("FRIEND_R"):
            idF=reply.split("|")[1]
            continue

        elif reply.startswith("ME"):
            print("You are:", reply.split("|")[1])

        elif reply.startswith("ONLINE"):
            print("Online list:", reply.split("|")[1])

        elif reply.startswith("ADDED"):
            print(f"Friend {reply.split("|")[1]} added!")

        elif reply.startswith("DENIED"):
            print(f"Friend {reply.split("|")[1]} DENIED your request!")

        elif reply == "REQUESTED":
            print("Friend request sent")

        elif reply == "INVALID":
            print("Invalid command")


if __name__=="__main__":
    login()
