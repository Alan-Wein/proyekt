import tkinter as tk
from tkinter import messagebox


def type(textbox,text):
    textbox.configure(state="normal")
    textbox.insert(tk.END, text)
    textbox.configure(state="disabled")
def textClear(textbox):
    textbox.configure(state="normal")
    textbox.delete("1.0",tk.END)
    textbox.configure(state="disabled")

def button_click(i,textbox):
    type(textbox,f"Friend {i}\n")

def _on_mousewheel(event,canvas):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")#how much scroll
def enter_pressed(entrybox, textbox):
    if entrybox.get() != "":
        type(textbox,"User> "+entrybox.get()+"\n")
        entrybox.delete(0, tk.END)


def popup(text):
    return messagebox.showinfo("",text)
def question(text):
    return messagebox.askyesno("",text)


def root(title,geometry,is_main:bool):
    root = tk.Tk()
    root.title = title
    root.geometry(geometry)
    if is_main:
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=0)
    else:
        root.resizable(False,False)
    root.update_idletasks()
    return root
def textbox(root):
    return tk.Text(root, font="Ariel", state="disabled", width=root.winfo_screenwidth())

def entrybox(root,is_password=False):
    entry= tk.Entry(root,font="Ariel")
    if is_password:
        entry.configure(show="*")
    return entry
def packF(self,anchor=None,padx=None,pady=None,fill=None): #pack Fake
    self.pack(anchor=anchor,padx=padx,pady=pady,fill=fill)
def label(root,text):
    return tk.Label(root, font="Ariel", text=text)

def button(root,text,comand=None):
    return tk.Button(root, text=text, command=comand)
def scrollbar(root,row,column,lst):

    right_area = tk.Frame(root)
    right_area.grid(row=row, column=column, sticky="ns")
    # Canvas + scrollbar
    canvas = tk.Canvas(right_area, width=160)
    canvas.grid(row=row, column=column-1, sticky="ns")

    scrollbar = tk.Scrollbar(right_area, orient="vertical", command=canvas.yview)
    scrollbar.grid(row=row, column=column, sticky="ns")

    canvas.configure(yscrollcommand=scrollbar.set)

    scrollable_frame = tk.Frame(canvas)
    scrollable_frame.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",lambda event: _on_mousewheel(event, canvas)))
    scrollable_frame.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    # Expand scroll region when size changes
    def update_scroll(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    scrollable_frame.bind("<Configure>", update_scroll)



    scrollable_frame.grid_columnconfigure(0, weight=1)

    return friends(scrollable_frame,canvas,lst)

def friends(scrollable_frame,canvas,friend_list):
    f_btns=[]
    if friend_list!= []:
        for i in range(len(friend_list)):
            btn = tk.Button(scrollable_frame, text=f"{friend_list[i][1]}", width=18)
            btn.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",lambda event: _on_mousewheel(event,canvas)))
            btn.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
            btn.grid(column=0, padx=5, pady=2, sticky="ew")
            var=friend_list[i][0]
            btn.hidden = var
            f_btns.append(btn)
    else:
        label1=label(scrollable_frame,"No_Friends")
        label1.grid(column=0, padx=5, pady=2, sticky="ew")

    return f_btns
