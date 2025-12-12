import tkinter as tk
import keyboard

def button_click(i,textbox):
    textbox.configure(state="normal")
    textbox.insert(tk.END,f"Friend {i}\n")
    textbox.configure(state="disabled")

def _on_mousewheel(event,canvas):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")#how much scroll
def type(entrybox, textbox):
    if entrybox.get() != "":
        textbox.configure(state="normal")
        textbox.insert(tk.END, ">"+entrybox.get()+"\n")
        textbox.configure(state="disabled")
        entrybox.delete(0, tk.END)
def root(title,geometry,is_main:bool):
    root = tk.Tk()
    root.title = title
    root.geometry(geometry)
    if is_main:
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=0)
    root.update_idletasks()
    return root
def textbox(root):
    return tk.Text(root, font="Ariel", state="disabled", width=root.winfo_screenwidth())

def entrybox(root):
    return tk.Entry(root,font="Ariel",width=root.winfo_screenwidth())

def label(root,text):
    return tk.Label(root, font="Ariel", text=text)

# def main_root(friend_list):
    # keyboard.add_hotkey('enter',type,args=(entrybox,textbox))
def scrollbar(root,row,column,lst,textbox):

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


    friends(scrollable_frame,canvas,lst,textbox)

    scrollable_frame.grid_columnconfigure(0, weight=1)

def friends(scrollable_frame,canvas,friend_list,textbox):
    for i in range(len(friend_list)):
        btn = tk.Button(scrollable_frame, text=f"{friend_list[i]}", width=18,command=lambda j=friend_list[i]: button_click(j,textbox))
        btn.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",lambda event: _on_mousewheel(event,canvas)))
        btn.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        btn.grid(column=0, padx=5, pady=2, sticky="ew")

