import tkinter as tk
from tkinter import messagebox
import tkinter.filedialog as fd
import re
import base64
import io


class GUI:
    def __init__(self):
        pass

    def down(self, textbox):
        textbox.see(tk.END)

    def type(self, textbox, text):
        textbox.configure(state="normal")
        textbox.insert(tk.END, text)
        textbox.configure(state="disabled")

    def get_input(self, entry):
        return entry.get()

    def get_toplevel(self, widget):
        return widget.winfo_toplevel()

    def clear_entry(self, entry):
        entry.delete(0, tk.END)

    def textClear(self, textbox):
        textbox.configure(state="normal")
        textbox.delete("1.0", tk.END)
        textbox.configure(state="disabled")

    def button_click(self, i, textbox):
        self.type(textbox, f"Friend {i}\n")

    def _on_mousewheel(self, event, canvas):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def enter_pressed(self, entrybox, textbox, name):
        if entrybox.get() != "":
            self.type(textbox, f"{name}> {entrybox.get()}\n")
            entrybox.delete(0, tk.END)

    def popup(self, text):
        return messagebox.showinfo("", text)

    def question(self, text):
        return messagebox.askyesno("", text)

    def checkbox(self, root, text, id):
        var = tk.IntVar(master=root, value=0)
        check = tk.Checkbutton(root, text=text, width=10, height=2, font=("Arial", 12), variable=var, onvalue=1,
                               offvalue=0)
        check.hidden = id
        check.var = var
        return check

    def frame(self, root, bd, relief):
        return tk.Frame(root, bd=bd, relief=relief)

    def root(self, title, geometry, is_main: bool):
        root = tk.Tk()
        root.title(title)
        root.geometry(geometry)
        if is_main:
            root.grid_columnconfigure(0, weight=1)
            root.grid_columnconfigure(1, weight=0)
        else:
            root.resizable(False, False)
        root.update_idletasks()
        return root

    def toplevel(self, title, geometry):
        top = tk.Toplevel()
        top.title(title)
        top.geometry(geometry)
        top.resizable(False, False)
        top.update_idletasks()
        return top

    def listbox(self, root):
        return tk.Listbox(root, font=("Arial", 12))

    def update_listbox(self, lb, items):
        lb.delete(0, tk.END)
        for item in items:
            lb.insert(tk.END, item)

    def scale(self, root, from_, to, orient="horizontal", command=None, default_val=0):
        s = tk.Scale(root, from_=from_, to=to, orient=orient, command=command, length=250)
        s.set(default_val)
        return s

    def textbox(self, root):
        return tk.Text(root, font="Arial", state="disabled", width=root.winfo_screenwidth())

    def entrybox(self, root, is_password=False):
        entry = tk.Entry(root, font="Arial")
        if is_password:
            entry.configure(show="*")
        return entry

    def label(self, root, text):
        return tk.Label(root, font="Arial", text=text)

    def button(self, root, text, comand=None):
        return tk.Button(root, text=text, command=comand)

    # --- NEW: Safe Chat Rendering Logic ---
    def render_chat_history(self, textbox, text_history):
        textbox.configure(state="normal")
        textbox.delete("1.0", tk.END)

        # Clear old memory references to avoid memory leaks
        if hasattr(textbox, "images"):
            textbox.images.clear()
        else:
            textbox.images = []

        if hasattr(textbox, "widgets"):
            for w in textbox.widgets:
                w.destroy()
            textbox.widgets.clear()
        else:
            textbox.widgets = []

        # Find our embedded File chunks
        pattern = r"<FILE::(.*?)::(.*?)>"
        last_idx = 0

        for match in re.finditer(pattern, text_history):
            before_text = text_history[last_idx:match.start()]
            if before_text:
                textbox.insert(tk.END, before_text)

            filename = match.group(1)
            b64_data = match.group(2)

            self._insert_file_ui(textbox, filename, b64_data)

            last_idx = match.end()

        remaining_text = text_history[last_idx:]
        if remaining_text:
            textbox.insert(tk.END, remaining_text)

        textbox.insert(tk.END, "\n")
        textbox.configure(state="disabled")
        self.down(textbox)

    def _insert_file_ui(self, textbox, filename, b64_data):
        def save_file_prompt(fname, b64_d):
            # The client decides where to save securely
            filepath = fd.asksaveasfilename(initialfile=fname, title="Save File")
            if filepath:
                try:
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64_d))
                    messagebox.showinfo("Success", f"File saved securely to:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file:\n{e}")

        ext = filename.lower().split('.')[-1]

        # If it's an image, decode it entirely in RAM (io.BytesIO)
        if ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp']:
            try:
                from PIL import Image, ImageTk
                image_data = base64.b64decode(b64_data)
                img = Image.open(io.BytesIO(image_data))
                img.thumbnail((250, 250))
                photo = ImageTk.PhotoImage(img)
                textbox.images.append(photo)

                textbox.image_create(tk.END, image=photo)
                textbox.insert(tk.END, "  ")
            except Exception:
                textbox.insert(tk.END, f"[Image Error] ")

        # Append a persistent Download Button inside the Textbox
        btn = tk.Button(textbox, text=f"📥 Save {filename}",
                        command=lambda f=filename, d=b64_data: save_file_prompt(f, d), cursor="hand2")

        textbox.widgets.append(btn)
        textbox.window_create(tk.END, window=btn)
        textbox.insert(tk.END, "\n")

    # ----------------------------------------

    def scrollbar(self, root, row, column, lst):
        right_area = tk.Frame(root)
        right_area.grid(row=row, column=column, sticky="ns")
        canvas = tk.Canvas(right_area, width=160)
        canvas.grid(row=row, column=column - 1, sticky="ns")

        scrollbar = tk.Scrollbar(right_area, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=row, column=column, sticky="ns")

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",
                                                                   lambda event: self._on_mousewheel(event, canvas)))
        scrollable_frame.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def update_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", update_scroll)
        scrollable_frame.grid_columnconfigure(0, weight=1)
        return self.friends(scrollable_frame, canvas, lst)

    def friends(self, scrollable_frame, canvas, friend_list):
        f_btns = []
        if friend_list != []:
            for i in range(len(friend_list)):
                btn = tk.Button(scrollable_frame, text=f"{friend_list[i][0]}", width=18)
                btn.bind("<Enter>",
                         lambda e: canvas.bind_all("<MouseWheel>", lambda event: self._on_mousewheel(event, canvas)))
                btn.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
                btn.grid(column=0, padx=5, pady=2, sticky="ew")
                var = friend_list[i][1]
                btn.hidden = var
                f_btns.append(btn)
        else:
            label1 = self.label(scrollable_frame, "No_Friends")
            label1.grid(column=0, padx=5, pady=2, sticky="ew")
        return f_btns
