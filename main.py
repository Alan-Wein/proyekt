import json
import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
            email text,
            name text,
            password text,
            id integer
            friends text
    )""")
conn.commit()
def start():
    email = input("Enter email: ")
    name = input("Enter name: ")
    password = input("Enter password: ")
    if email == "e" and name == "e" and password == "e":
        return
    c.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    if(c.fetchone() is None):
        c.execute("SELECT COUNT(*) FROM users")
        id = c.fetchone()[0]
        c.execute("""INSERT INTO users VALUES (?, ?, ?, ?)""", (email, name, password, id))
        print("Hello for the first time!")
        conn.commit()
        chat(id)
    else:
        c.execute("SELECT 1 FROM users WHERE name = ? AND password = ?" , (name,password))
        if c.fetchone() is None:
            print("name or password are incorrect")
            start()
        else:
            print("Welcome back!")
        conn.commit()
        chat(id)
conn.close()

def chat(id):
    while True:
        text=input("")
        if text=="list":
            c.execute("SELECT friends FROM users Where id=?",(id,))
            lst = c.fetchone()
            print(json.load(lst))
        if text.startswith("add "):
            value = text[4:]
            if value.strip():
                print("h")
            else:
                print("Invalid: nothing after 'add'")

