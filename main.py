import socket
import threading
import time
idF=-1
def start():
    s = socket.socket()
    s.connect(("127.0.0.1", 9999))

    email = input("Enter email: ")
    name = input("Enter name: ")
    password = input("Enter password: ")
    if email == "e" and name == "e" and password == "e":
        s.send("EXIT".encode())
        return
    if email == "clear" and name == "e" and password == "e":
        s.send("CLEAR".encode())
        start()
        return
    else:
        s.send(f"LOGIN|{email}|{name}|{password}".encode())
    response = s.recv(2048).decode()

    if response == "NO":
        print("Name or password incorrect")
        start()

    elif response.startswith("NEW"):
        id = response.split("|")[1]
        print("Hello for the first time!")

    elif response.startswith("OK"):
        id = response.split("|")[1]
        print("Welcome back!")

    threading.Thread(target=listen, args=(s,)).start()
    talk(s,id)

def talk(s,id):
    global idF
    while True:
        # print(idF)
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
                break
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
            print("> ",end="")

        elif reply.startswith("DENIED"):
            print(f"Friend {reply.split("|")[1]} DENIED your request!")
            print("> ",end="")

        elif reply == "REQUESTED":
            print("Friend request sent")

        elif reply == "INVALID":
            print("Invalid command")


if __name__=="__main__":
    start()
