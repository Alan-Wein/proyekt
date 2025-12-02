import tkinter as tk
root = tk.Tk()
def button_click(i):
    textbox.insert(tk.END,f"Friend {i}\n")

def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

root.title="program"
root.grid_columnconfigure(0, weight=1)  # left side expands
root.grid_columnconfigure(1, weight=0)  # right side fixed
textbox=tk.Text(root,font="Ariel")
textbox.grid(row=1,column=0,padx=10,pady=1,rowspan=10)
label=tk.Label(root,font="Ariel",text="Hello")
label.grid(row=0,column=1,padx=10,pady=5)
label2=tk.Label(root,font="Ariel",text="Chat",anchor="center")
label2.grid(row=0,column=0,padx=10,pady=1)
right_area = tk.Frame(root)
right_area.grid(row=2, column=1, sticky="ns")

# Canvas + scrollbar
canvas = tk.Canvas(right_area, width=160)
canvas.grid(row=2, column=0, sticky="ns")

scrollbar = tk.Scrollbar(right_area, orient="vertical", command=canvas.yview)
scrollbar.grid(row=2, column=1, sticky="ns")

canvas.configure(yscrollcommand=scrollbar.set)

scrollable_frame = tk.Frame(canvas)
scrollable_frame.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
scrollable_frame.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

# Expand scroll region when size changes
def update_scroll(event):
    canvas.configure(scrollregion=canvas.bbox("all"))
scrollable_frame.bind("<Configure>", update_scroll)

lst=[]
for i in range(20):
    btn = tk.Button(scrollable_frame, text=f"Butt {i+1}", width=18,command=lambda i=i: button_click(i+1))
    btn.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
    btn.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
    btn.grid(row=i, column=0, padx=5, pady=2, sticky="ew")

scrollable_frame.grid_columnconfigure(0, weight=1)


root.mainloop()
