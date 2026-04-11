import tkinter as tk
from tkinter import messagebox
class GUI:
    def __init__(self):
        pass
    def down(self,textbox):
        textbox.see(tk.END)
    def type(self,textbox,text):
        textbox.configure(state="normal")
        textbox.insert(tk.END, text)
        textbox.configure(state="disabled")
    def textClear(self,textbox):
        textbox.configure(state="normal")
        textbox.delete("1.0",tk.END)
        textbox.configure(state="disabled")

    def button_click(self,i,textbox):
        self.type(textbox,f"Friend {i}\n")

    def _on_mousewheel(self,event,canvas):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")#how much scroll
    def enter_pressed(self,entrybox, textbox,name):
        if entrybox.get() != "":
            self.type(textbox,f"{name}> {entrybox.get()}\n")
            entrybox.delete(0, tk.END)


    def popup(self,text):
        return messagebox.showinfo("",text)

    def question(self,text):
        return messagebox.askyesno("",text)

    def checkbox(self,root,text,id):
        var = tk.IntVar(master=root,value=0)
        check=tk.Checkbutton(root,text=text,width=10,height=2,font=("Arial",12),variable=var,onvalue=1, offvalue=0)
        check.hidden=id
        check.var=var
        return check





    def frame(self,root,bd,relief):
        return tk.Frame(root,bd=bd,relief=relief)

    def root(self,title,geometry,is_main:bool):
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
    def textbox(self,root):
        return tk.Text(root, font="Ariel", state="disabled", width=root.winfo_screenwidth())

    def entrybox(self,root,is_password=False):
        entry= tk.Entry(root,font="Ariel")
        if is_password:
            entry.configure(show="*")
        return entry
    # def packF(self,anchor=None,padx=None,pady=None,fill=None): #pack Fake
    #     self.pack(anchor=anchor,padx=padx,pady=pady,fill=fill)
    def label(self,root,text):
        return tk.Label(root, font="Ariel", text=text)

    def button(self,root,text,comand=None):
        return tk.Button(root, text=text, command=comand)
    def scrollbar(self,root,row,column,lst):

        right_area = tk.Frame(root)
        right_area.grid(row=row, column=column, sticky="ns")
        canvas = tk.Canvas(right_area, width=160)
        canvas.grid(row=row, column=column-1, sticky="ns")

        scrollbar = tk.Scrollbar(right_area, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=row, column=column, sticky="ns")

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",lambda event: self._on_mousewheel(event, canvas)))
        scrollable_frame.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # expand scroll region when size changes
        def update_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable_frame.bind("<Configure>", update_scroll)
        scrollable_frame.grid_columnconfigure(0, weight=1)
        return self.friends(scrollable_frame,canvas,lst)

    def friends(self,scrollable_frame,canvas,friend_list):
        f_btns=[]
        if friend_list!= []:
            for i in range(len(friend_list)):
                btn = tk.Button(scrollable_frame, text=f"{friend_list[i][0]}", width=18)
                btn.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",lambda event: self._on_mousewheel(event,canvas)))
                btn.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
                btn.grid(column=0, padx=5, pady=2, sticky="ew")
                var=friend_list[i][1]
                btn.hidden = var
                f_btns.append(btn)
        else:
            label1=self.label(scrollable_frame,"No_Friends")
            label1.grid(column=0, padx=5, pady=2, sticky="ew")

        return f_btns
