import json, socket, threading, keyboard, os
import tkinter.filedialog as fd
import pyaudio
import GUI
import hashlib, struct, math, base64


# --- ROBUST SOCKET FRAMING ---
def send_msg(sock, msg):
    try:
        encoded = msg.encode('utf-8')
        header = f"{len(encoded):<16}".encode('utf-8')
        sock.sendall(header + encoded)
    except:
        pass


def recv_msg(sock):
    try:
        header = sock.recv(16)
        if not header: return ""
        length = int(header.decode('utf-8').strip())
        data = b""
        while len(data) < length:
            chunk = sock.recv(min(4096, length - len(data)))
            if not chunk: break
            data += chunk
        return data.decode('utf-8')
    except:
        return ""


# -----------------------------
SERVER_IP="127.0.0.1"


in_chat = None
s = socket.socket()
s.connect((SERVER_IP, 9999))

f_btns = []
friends = []
gui = GUI.GUI()

# Voice Chat Globals
vc_running = False
vc_socket = None
vc_listbox = None
vc_root_window = None
vc_mute_btn = None
is_muted = False
current_user_id = None
main_textbox = None

# Settings Globals
noise_threshold = 0
current_mute_keybind = ""
mute_hotkey_hook = None
test_mic_running = False


def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


def get_rms(data):
    count = len(data) // 2
    if count == 0: return 0
    shorts = struct.unpack(f"<{count}h", data)
    sum_squares = sum(s * s for s in shorts)
    return math.sqrt(sum_squares / count)


def btn_create(list, id):
    for b in list:
        f_list = b.hidden
        f_list.append(int(id))
        b.configure(command=lambda friends=f_list: button_click(friends))


def button_click(friends_lst):
    send_msg(s, f"CHAT_START|{json.dumps(friends_lst)}")


def closed(root):
    global vc_running
    if vc_running:
        leave_call(None)
    send_msg(s, "EXIT")
    root.destroy()


def enter_pressed(entrybox, textbox, id, name):
    text = gui.get_input(entrybox)
    if text == "": return

    if in_chat is not None:
        send_msg(s, f"CHAT|{id}|{in_chat}|{text}")
        gui.clear_entry(entrybox)
    elif text == "/exit":
        closed(gui.get_toplevel(entrybox))
    elif text.startswith("/"):
        send_msg(s, f"CMD|{id}|{text[1:]}")
        gui.clear_entry(entrybox)


def upload_file(id, name):
    if in_chat is None:
        gui.popup("Please select a chat first.")
        return

    filepath = fd.askopenfilename()
    if not filepath: return

    filesize = os.path.getsize(filepath)
    if filesize > 10 * 1024 * 1024:
        gui.popup("File exceeds 10MB limit.")
        return

    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode('utf-8')

    send_msg(s, f"FILE|{id}|{in_chat}|{filename}|{b64_data}")


def pressed(id, root, name, checkboxes):
    if name == "":
        root.attributes('-topmost', False)
        gui.popup("Group name not entered")
        root.attributes('-topmost', True)
        return
    lst = [int(id)]
    for cb in checkboxes:
        if cb.var.get() == 1:
            lst.append(cb.hidden[0])
    if len(lst) < 3:
        root.attributes('-topmost', False)
        gui.popup("Not enough checkboxes have been pressed")
        root.attributes('-topmost', True)
        return
    send_msg(s, f"GROUP|{lst}|{name}")
    root.destroy()


def group(id):
    root = gui.root("Group Create", "500x500", False)
    root.attributes('-topmost', True)
    BOXES_PER_ROW = 3

    entrybox = gui.entrybox(root)
    entrybox.grid(column=0, row=1, columnspan=BOXES_PER_ROW)
    lst = []
    for i in range(len(friends)):
        if len(friends[i][1]) < 3:
            lst.append(friends[i])
    checkboxes = []
    for i in range(len(lst)):
        row = i // BOXES_PER_ROW
        col = i % BOXES_PER_ROW
        checkbox = gui.checkbox(root, lst[i][0], lst[i][1])
        checkbox.grid(row=row + 2, column=col, padx=10, pady=10)
        checkboxes.append(checkbox)
    buttonCreate = gui.button(root, "Create Group", lambda: pressed(id, root, entrybox.get(), checkboxes))
    buttonCreate.grid(row=0, column=0, columnspan=BOXES_PER_ROW, pady=10, padx=10)
    root.mainloop()


def login(root, entryE, entryU, entryP):
    email = entryE.get()
    name = entryU.get()
    raw_password = entryP.get()

    if email == "e" and name == "e" and raw_password == "e":
        send_msg(s, "EXIT")
        root.destroy()
        return
    if email == "clear" and name == "e" and raw_password == "e":
        send_msg(s, "CLEAR")
        entryE.delete(0, "end")
        entryU.delete(0, "end")
        entryP.delete(0, "end")
        return
    else:
        password_hash = hash_password(raw_password)
        send_msg(s, f"LOGIN|{email}|{name}|{password_hash}")

    response = recv_msg(s)

    if response == "ONLINE":
        gui.popup("Client already connected elsewhere")
        entryE.delete(0, "end")
        entryU.delete(0, "end")
        entryP.delete(0, "end")
        return

    if response == "NO":
        gui.popup("Name or password incorrect. Try again")
        entryE.delete(0, "end")
        entryU.delete(0, "end")
        entryP.delete(0, "end")
        return

    elif response.startswith("NEW") or response.startswith("OK"):
        parts = response.split("|")
        id = parts[1]
        if len(parts) > 2:
            try:
                stgs = json.loads(parts[2])
                set_noise_threshold(stgs.get("noise", 0))
                set_mute_keybind(stgs.get("keybind", ""), silent=True)
            except:
                pass
        root.destroy()
        start(id)


def begin():
    root = gui.root("Login", "400x320", False)
    gui.label(root, text="Email:").pack(anchor="w", padx=20, pady=(15, 0))
    entryE = gui.entrybox(root)
    entryE.pack(fill="x", padx=20)
    gui.label(root, text="Username:").pack(anchor="w", padx=20, pady=(10, 0))
    entryU = gui.entrybox(root)
    entryU.pack(fill="x", padx=20)
    gui.label(root, text="Password:").pack(anchor="w", padx=20, pady=(10, 0))
    entryP = gui.entrybox(root, True)
    entryP.pack(fill="x", padx=20)
    button = gui.button(root, text="Log In", comand=lambda: login(root, entryE, entryU, entryP))
    button.pack(pady=20)
    root.protocol("WM_DELETE_WINDOW", lambda: closed(root))
    root.mainloop()


def update_call_button(btn, status, user_id, room_key):
    if status == "ON":
        btn.configure(text="Join Call (Active)", fg="green", state="normal",
                      command=lambda: join_call(user_id, room_key, False))
    else:
        btn.configure(text="Start call", fg="black", state="normal", command=lambda: join_call(user_id, room_key, True))


# ---- SETTINGS FUNCTIONS ----
def open_settings(id):
    root = gui.toplevel("Settings", "400x550")

    gui.label(root, "--- Password Reset ---").pack(pady=(10, 0))
    gui.label(root, "Email:").pack()
    entry_email = gui.entrybox(root)
    entry_email.pack()
    gui.label(root, "Old Password:").pack()
    entry_old = gui.entrybox(root, is_password=True)
    entry_old.pack()
    gui.label(root, "New Password:").pack()
    entry_new = gui.entrybox(root, is_password=True)
    entry_new.pack()
    gui.button(root, "Reset Password",
               lambda: reset_password(entry_email.get(), entry_old.get(), entry_new.get())).pack(pady=5)

    gui.label(root, "--- Voice Chat Settings ---").pack(pady=(20, 0))
    gui.label(root, "Mute Keybind (e.g., 'm', 'ctrl+m', or empty):").pack()
    entry_keybind = gui.entrybox(root)
    entry_keybind.insert(0, current_mute_keybind)
    entry_keybind.pack()
    gui.button(root, "Set Keybind", lambda: set_mute_keybind(entry_keybind.get())).pack(pady=5)

    gui.label(root, "Noise Suppression Threshold (dB / Amplitude):").pack()
    scale = gui.scale(root, 0, 1000, "horizontal", lambda val: set_noise_threshold(val), noise_threshold)
    scale.pack()

    test_btn = gui.button(root, "Test Mic (Echo w/ Delay)", None)
    test_btn.configure(command=lambda: toggle_test_mic(test_btn))
    test_btn.pack(pady=10)

    root.protocol("WM_DELETE_WINDOW", lambda: close_settings(root, test_btn))


def reset_password(email, old_raw, new_raw):
    if not email or not old_raw or not new_raw:
        gui.popup("Please fill all fields.")
        return
    old_hash = hash_password(old_raw)
    new_hash = hash_password(new_raw)
    send_msg(s, f"RESET_PASS|{email}|{old_hash}|{new_hash}")


def set_mute_keybind(key_str, silent=False):
    global current_mute_keybind, mute_hotkey_hook
    if current_mute_keybind and mute_hotkey_hook:
        try:
            keyboard.remove_hotkey(mute_hotkey_hook)
        except:
            pass
    current_mute_keybind = key_str
    if key_str:
        try:
            mute_hotkey_hook = keyboard.add_hotkey(key_str, toggle_mute_from_hotkey)
            if not silent: gui.popup(f"Keybind set to: {key_str}")
        except Exception as e:
            if not silent: gui.popup(f"Invalid keybind: {e}")
            current_mute_keybind = ""
    else:
        if not silent: gui.popup("Keybind disabled.")


def toggle_mute_from_hotkey():
    global vc_mute_btn
    if vc_running and vc_mute_btn:
        toggle_mute(vc_mute_btn)


def set_noise_threshold(val):
    global noise_threshold
    noise_threshold = float(val)


def toggle_test_mic(btn):
    global test_mic_running
    test_mic_running = not test_mic_running
    btn.config(text="Stop Test" if test_mic_running else "Test Mic (Echo w/ Delay)")
    if test_mic_running:
        threading.Thread(target=mic_test_thread, daemon=True).start()


def mic_test_thread():
    CHUNK = 1024
    p = pyaudio.PyAudio()
    stream_in = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=CHUNK)
    stream_out = p.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True, frames_per_buffer=CHUNK)
    delay_buffer = []
    while test_mic_running:
        try:
            data = stream_in.read(CHUNK, exception_on_overflow=False)
            rms = get_rms(data)
            if rms >= noise_threshold:
                delay_buffer.append(data)
            else:
                delay_buffer.append(b'\x00' * len(data))

            if len(delay_buffer) > 21:
                play_data = delay_buffer.pop(0)
                stream_out.write(play_data)
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    stream_in.stop_stream()
    stream_in.close()
    stream_out.stop_stream()
    stream_out.close()
    p.terminate()


def close_settings(root, test_btn):
    global test_mic_running
    if test_mic_running:
        toggle_test_mic(test_btn)

    stgs = json.dumps({"noise": noise_threshold, "keybind": current_mute_keybind})
    send_msg(s, f"UPDATE_SETTINGS|{current_user_id}|{stgs}")
    root.destroy()


def start(id):
    global friends, current_user_id, main_textbox
    current_user_id = id

    root = gui.root("Chat App", "1000x600", True)

    toolbar = gui.frame(root, bd=1, relief="raised")
    toolbar.grid(row=0, column=0, sticky="ew")

    btn_quit = gui.button(toolbar, text="Quit", comand=lambda: closed(root))
    btn_quit.grid(row=0, column=0, padx=5, pady=5)

    call = gui.button(toolbar, text="Start call")
    call.configure(state="disabled")
    call.grid(row=0, column=1, padx=5, pady=5)

    btn_settings = gui.button(toolbar, text="Settings", comand=lambda: open_settings(id))
    btn_settings.grid(row=0, column=2, padx=5, pady=5)

    main_textbox = gui.textbox(root)
    main_textbox.grid(row=1, column=0, padx=10, pady=1, rowspan=5)

    bottom_frame = gui.frame(root, bd=0, relief="flat")
    bottom_frame.grid(row=10, column=0, padx=10, pady=1, sticky="ew")

    entry = gui.entrybox(bottom_frame)
    entry.pack(side="left", fill="x", expand=True)

    send_msg(s, f"CMD|{id}|me")
    reply = recv_msg(s).split("|")
    name = reply[2]

    btn_upload = gui.button(bottom_frame, text="+", comand=lambda: upload_file(id, name))
    btn_upload.pack(side="right", padx=5)

    keyboard.add_hotkey('enter', lambda: enter_pressed(entry, main_textbox, id, name))

    buttonGroup = gui.button(root, "Create Group", comand=lambda: group(id))
    buttonGroup.grid(row=1, column=1, padx=10, pady=1)

    entryADD = gui.entrybox(root)
    entryADD.grid(row=3, column=1, padx=10, pady=1)

    buttonADD = gui.button(root, "Add Friend(input id)", comand=lambda: addFriend(id, entryADD))
    buttonADD.grid(row=2, column=1, padx=10, pady=1)

    labelF = gui.label(root, "Friend List")
    labelF.grid(row=4, column=1, padx=10, pady=5)

    send_msg(s, f"CMD|{id}|list")
    friends_data = recv_msg(s)
    if "|" in friends_data:
        friends = json.loads(friends_data.split("|")[1])
        f_btns = gui.scrollbar(root, 5, 1, friends)
        btn_create(f_btns, id)

    send_msg(s, f"OFFLINE|{id}")
    threading.Thread(target=listen, args=(s, root, main_textbox, id, call), daemon=True).start()

    root.protocol("WM_DELETE_WINDOW", lambda: closed(root))
    root.mainloop()


def addFriend(id, entryADD):
    send_msg(s, f"CMD|{id}|add {entryADD.get()}")
    entryADD.delete(0, "end")


# ---- VOICE CHAT FUNCTIONS ----
def join_call(id, room_key, is_initiator=False):
    global vc_running, vc_socket, is_muted, vc_listbox, vc_root_window, vc_mute_btn, noise_threshold

    if vc_running:
        gui.popup("You are already in a call!")
        return

    vc_running = True
    is_muted = False

    vc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    vc_socket.bind(("0.0.0.0", 0))
    vc_socket.sendto(f"REG|{id}".encode(), (SERVER_IP, 9998))

    vc_root_window = gui.toplevel("Voice Chat", "300x400")

    lbl = gui.label(vc_root_window, "Participants in call:")
    lbl.pack(pady=10)

    vc_listbox = gui.listbox(vc_root_window)
    vc_listbox.pack(fill="both", expand=True, padx=20, pady=5)

    vc_mute_btn = gui.button(vc_root_window, "Mute", comand=lambda: toggle_mute(vc_mute_btn))
    vc_mute_btn.pack(pady=10)

    leave_btn = gui.button(vc_root_window, "Leave Call", comand=lambda: leave_call(vc_root_window))
    leave_btn.pack(pady=10)

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    p = pyaudio.PyAudio()

    input_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    output_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

    def record_audio():
        while vc_running:
            try:
                data = input_stream.read(CHUNK, exception_on_overflow=False)
                rms = get_rms(data)
                if not is_muted and vc_socket and rms >= noise_threshold:
                    vc_socket.sendto(data, (SERVER_IP, 9998))
            except:
                break

    def play_audio():
        while vc_running:
            try:
                if vc_socket:
                    data, _ = vc_socket.recvfrom(4096)
                    if not data.startswith(b"REG|"):
                        output_stream.write(data)
            except:
                break

    threading.Thread(target=record_audio, daemon=True).start()
    threading.Thread(target=play_audio, daemon=True).start()

    vc_root_window.cleanup_audio = lambda: (
        input_stream.stop_stream(), input_stream.close(),
        output_stream.stop_stream(), output_stream.close(), p.terminate()
    )
    vc_root_window.protocol("WM_DELETE_WINDOW", lambda: leave_call(vc_root_window))

    if is_initiator:
        send_msg(s, f"CALL_INIT|{room_key}|{id}")
    else:
        send_msg(s, f"CALL_ACCEPT|{room_key}|{id}")


def toggle_mute(btn):
    global is_muted
    is_muted = not is_muted
    btn.config(text="Unmute" if is_muted else "Mute")


def leave_call(vc_root=None):
    global vc_running, vc_socket, current_user_id, vc_listbox, vc_root_window, vc_mute_btn
    if not vc_running: return
    vc_running = False
    send_msg(s, f"CALL_LEAVE|{current_user_id}")

    if vc_socket:
        try:
            vc_socket.close()
        except:
            pass
        vc_socket = None

    target = vc_root or vc_root_window
    if target:
        try:
            target.cleanup_audio()
        except:
            pass
        try:
            target.destroy()
        except:
            pass

    vc_listbox = None
    vc_root_window = None
    vc_mute_btn = None


def listen(s, root, textbox, id, call):
    global friends, in_chat, vc_listbox

    while True:
        reply = recv_msg(s)
        if not reply: break

        is_down = textbox.yview()[1] == 1.0
        parts = reply.split("|")
        text = ""

        if reply == "EXIT":
            root.destroy()
            break

        elif parts[0] == "RESET_OK":
            gui.popup("Password reset successfully!")
            continue

        elif parts[0] == "RESET_FAIL":
            gui.popup("Password reset failed. Check your email and old password.")
            continue

        elif parts[0] == "FRIENDS":
            text = "Friends list:" + parts[1]

        elif parts[0] == "FRIEND_R":
            idf = parts[1]
            answer = gui.question(f"Do you want to be friends with {idf}?")
            text_ans = "Y" if answer else "N"
            send_msg(s, f"FRIEND_A|{id}|{idf}|{text_ans}")
            continue

        elif parts[0] == "ME":
            text = "You are:" + parts[1]

        elif parts[0] == "ONLINE":
            text = "Online list:" + parts[1]

        elif parts[0] == "ADDED":
            gui.popup(f"{parts[1]} added!")
            send_msg(s, f"CMD|{id}|list")
            friends_data = recv_msg(s)
            if "|" in friends_data:
                friends = json.loads(friends_data.split("|")[1])
                f_btns = gui.scrollbar(root, 5, 1, friends)
                btn_create(f_btns, id)
            send_msg(s, f"DONE|{id}")
            continue

        elif parts[0] == "CHAT_START":
            in_chat = parts[1]
            call_status = parts[2]
            text = reply.split("|", 3)[3] if len(parts) > 3 else ""

            # Replaced the standard text insert with our smart history renderer
            gui.render_chat_history(textbox, text)
            update_call_button(call, call_status, id, in_chat)
            continue

        elif parts[0] == "CALL_STATE":
            room_key = parts[1]
            status = parts[2]
            if in_chat == room_key:
                update_call_button(call, status, id, in_chat)
            continue

        elif parts[0] == "CHAT":
            list_id = parts[2]
            if in_chat == list_id:
                # Reload chat to pull in the new standard message or the new embedded file
                send_msg(s, f"CHAT_START|{list_id}")
            continue

        elif parts[0] == "CALLING":
            room_key = parts[1]
            caller_id = parts[2]
            caller_name = parts[3]
            answer = gui.question(f"{caller_name} started a voice call. Join now?")
            if answer:
                join_call(id, room_key, False)
            continue

        elif parts[0] == "VC_enter" or parts[0] == "VC_leave":
            text = parts[1]
            gui.type(textbox, f"System> {text}\n")
            if is_down: gui.down(textbox)
            continue

        elif parts[0] == "VC_UPDATE":
            participants = json.loads(parts[1])
            if vc_listbox:
                vc_listbox.after(0, lambda p=participants: gui.update_listbox(vc_listbox, p))
            continue

        elif parts[0] == "DENIED":
            gui.popup(f"Friend {parts[1]} DENIED your request!")
            continue

        elif reply == "REQUESTED":
            gui.popup("Friend request sent!")
            continue

        elif reply == "INVALID":
            gui.popup("INVALID ACTION")
            continue
        else:
            text = "Server Error/Unknown"

        if text:
            gui.type(textbox, "Server> " + text + '\n')
            if is_down: gui.down(textbox)


if __name__ == "__main__":
    begin()
