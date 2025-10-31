import json
import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
            email TEXT,
            name TEXT,
            password TEXT,
            id INTEGER,
            friends Text
    )""")
conn.commit()
def start():
    email = input("Enter email: ")
    name = input("Enter name: ")
    password = input("Enter password: ")
    c.execute("SELECT COUNT(*) FROM users")
    id = c.fetchone()[0]
    lst=[]
    if email == "e" and name == "e" and password == "e":
        return
    if email == "clear" and name == "e" and password == "e":
        c.execute("DELETE FROM users")
        start()
    c.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    if(c.fetchone() is None):

        c.execute("""INSERT INTO users VALUES (?, ?, ?, ?, ?)""", (email, name, password, id, json.dumps(lst)))
        print("Hello for the first time!")
        conn.commit()
        chat(id)
    else:
        c.execute("SELECT 1 FROM users WHERE name = ? AND password = ?" , (name,password))
        if c.fetchone() is None:
            print("name or password are incorrect")
            start()
        else:
            c.execute("SELECT id FROM users WHERE name = ?", (name,))
            id=c.fetchone()[0]
            print("Welcome back!")
        conn.commit()
        chat(id)

def chat(id):
    c.execute("SELECT COUNT(*) FROM users")
    user_len = c.fetchone()[0]
    while True:
        c.execute("SELECT * FROM users Where id=?", (id,))
        user = c.fetchone()
        lst = json.loads(user[4])
        text=input("")
        if text=="list":
            print("Friends list: " +lst.__str__())
        if text == "exit":
            break
        if text == "back":
            start()
            break
        if text.startswith("add "):
            value = text[4:].strip()
            if value.isdigit() and value != "" and int(value)<user_len and int(value) not in lst and int(value)!=id:
                lst.append(int(value))
                c.execute("""UPDATE users SET friends = ? WHERE id = ?""",(json.dumps(lst),id))
                conn.commit()
            else:
                print("Invalid \"add\" ")


if __name__ == "__main__":
    start()
