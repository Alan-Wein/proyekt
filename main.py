import socket

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
        exit()

    elif response.startswith("NEW"):
        id = response.split("|")[1]
        print("Hello for the first time!")

    elif response.startswith("OK"):
        id = response.split("|")[1]
        print("Welcome back!")

    # Chat loop
    while True:
        text = input("> ")
        if text == "exit":
            s.send("EXIT".encode())
            print("Goodbye")
            break

        s.send(f"CMD|{id}|{text}".encode())
        reply = s.recv(2048).decode()

        if reply.startswith("FRIENDS"):
            print("Friends list:", reply.split("|")[1])

        elif reply.startswith("ME"):
            print("You are:", reply.split("|")[1])

        elif reply.startswith("ONLINE"):
            print("Online list:", reply.split("|")[1])

        elif reply == "ADDED":
            print("Friend added")

        elif reply == "INVALID":
            print("Invalid command")


if __name__=="__main__":
    start()
