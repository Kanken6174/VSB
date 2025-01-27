# gui.py
import tkinter as tk
import os
from tkinter import messagebox
from parser import find_blocks
from gui_components import EntityBlock, AdapterBlock
from generator import generate_top_level
import json

def load_previous_configuration(canvas,json_path):
    if not os.path.exists(json_path):
        return
    with open(json_path,"r") as f:
        data=json.load(f)
    blocks_data=data.get("blocks",[])
    connections_data=data.get("connections",[])
    new_blocks=[]
    for bd in blocks_data:
        t=bd["type"]
        n=bd["name"]
        x=bd["x"]
        y=bd["y"]
        if t=="adapter":
            ab=AdapterBlock(canvas,x,y,{"kind":"SLV","width":1},{"kind":"SLV","width":1},"Convert") 
            ab.name=n
            canvas.itemconfig(ab.text,text=n)
            ab.x=x
            ab.y=y
            coords=canvas.coords(ab.obj)
            cx=(coords[0]+coords[4])/2
            cy=(coords[1]+coords[5])/2
            dx=x-cx
            dy=y-cy
            canvas.move(ab.obj,dx,dy)
            canvas.move(ab.text,dx,dy)
            ab.left_port.x=x-30
            ab.left_port.y=y
            ab.right_port.x=x+30
            ab.right_port.y=y
            canvas.move(ab.left_port.id,dx,dy)
            canvas.move(ab.left_port.label_id,dx,dy)
            canvas.move(ab.right_port.id,dx,dy)
            canvas.move(ab.right_port.label_id,dx,dy)
            new_blocks.append(ab)
        else:
            gen=bd.get("generics",[])
            ports=bd.get("ports",[])
            ent_ports=[]
            for p in ports:
                ent_ports.append({"name":p["port_name"],"dir":p["port_dir"],"type":p["port_type"]})
            eb=EntityBlock(canvas,x,y,n,gen,ent_ports,bd.get("conduit",False))
            eb.name=n
            eb.x=x
            eb.y=y
            if bd.get("generic_values"):
                eb.generic_values=bd["generic_values"]
            coords=canvas.coords(eb.obj)
            dx=x-coords[0]
            dy=y-coords[1]
            canvas.move(eb.obj,dx,dy)
            canvas.move(eb.title_id,dx,dy)
            for i,ps in enumerate(eb.port_symbols):
                px=ports[i]["x"]
                py=ports[i]["y"]
                pdx=px-ps.x
                pdy=py-ps.y
                ps.x=px
                ps.y=py
                canvas.move(ps.id,pdx,pdy)
                canvas.move(ps.label_id,pdx,pdy)
                ps.is_conduit=ports[i]["is_conduit"]
                if ps.is_conduit:
                    canvas.itemconfig(ps.id,outline="red")
            new_blocks.append(eb)
    canvas.data["blocks"].extend(new_blocks)
    name_map={}
    for b in new_blocks:
        name_map[b.name]=b
    ports_map={}
    for b in new_blocks:
        for ps in b.port_symbols:
            ports_map[(b.name,ps.port["name"])]=ps
    for c in connections_data:
        block1=c["block1"]
        block2=c["block2"]
        port1=c["port1"]
        port2=c["port2"]
        if (block1,port1) in ports_map and (block2,port2) in ports_map:
            p1=ports_map[(block1,port1)]
            p2=ports_map[(block2,port2)]
            if p1.color:
                line_color=p1.color
            else:
                line_color="black"
            line=canvas.create_line(p1.x,p1.y,p2.x,p2.y,fill=line_color,tags=("wire",),smooth=True,splinesteps=36,width=3)
            canvas.data["connections"].append((p1,p2,line,None))
            cx1=p1.x+(p2.x-p1.x)/2
            cy1=p1.y
            cx2=p1.x+(p2.x-p1.x)/2
            cy2=p2.y
            canvas.coords(line,p1.x,p1.y,cx1,cy1,cx2,cy2,p2.x,p2.y)
    for w in canvas.find_withtag("wire"):
        canvas.tag_bind(w,"<Button-3>",lambda e: wire_right_click(e,canvas))

def wire_right_click(event,canvas):
    wire=canvas.find_closest(event.x,event.y)[0]
    if "wire" in canvas.gettags(wire):
        menu=tk.Menu(canvas,tearoff=0)
        menu.add_command(label="Disconnect",command=lambda:disconnect_wire(canvas,wire))
        menu.post(event.x_root,event.y_root)

def disconnect_wire(canvas,wire_id):
    canvas.delete(wire_id)
    cs=canvas.data["connections"]
    to_del=[c for c in cs if c[2]==wire_id]
    for td in to_del:
        cs.remove(td)

def run_gui(directory):
    blocks=find_blocks(directory)
    root=tk.Tk()
    root.title("Efinix System Builder")
    left_frame=tk.Frame(root)
    left_frame.pack(side="left",fill="y",padx=5,pady=5)
    tk.Label(left_frame,text="Available Blocks").pack()
    blocks_listbox=tk.Listbox(left_frame)
    blocks_listbox.pack(fill="both",expand=True)
    for block in blocks:
        name,generics,ports=block
        if generics==[] and ports==[]:
            block_type="Empty Block"
        else:
            block_type="Entity/Component"
        blocks_listbox.insert("end",f"{block_type}: {name}")
    add_conduit_button=tk.Button(left_frame,text="New Conduit",command=lambda:add_conduit(root,canvas))
    add_conduit_button.pack(pady=5,fill="x")
    generate_button=tk.Button(left_frame,text="Generate TopLevel",command=lambda:generate_top_level(canvas))
    generate_button.pack(pady=5,fill="x")
    right_frame=tk.Frame(root)
    right_frame.pack(side="right",expand=True,fill="both")
    canvas=tk.Canvas(right_frame,bg="white")
    canvas.pack(expand=True,fill="both")
    canvas.data={
        "connections":[],
        "blocks":[],
        "port_map":{},
        "active_line":None,
        "active_port":None,
        "project_root":directory
    }
    load_previous_configuration(canvas,os.path.join(directory,"TopLevelAdapter.json"))
    def start_drag(event):
        selection=blocks_listbox.curselection()
        if selection:
            index=selection[0]
            item=blocks_listbox.get(index)
            block_info=item.split(": ")
            if len(block_info)==2:
                block_type,block_name=block_info
                selected_block=next((b for b in blocks if b[0]==block_name),None)
                if selected_block:
                    canvas.data["drag_block"]=selected_block
                    canvas.data["drag_label"]=tk.Label(left_frame,text=block_name,bg="lightgreen")
                    canvas.data["drag_label"].place(x=event.x,y=event.y)
                    blocks_listbox.bind("<Motion>",on_drag_motion)
                    blocks_listbox.bind("<ButtonRelease-1>",on_drag_release)
    def on_drag_motion(event):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].place(x=event.x,y=event.y)
    def on_drag_release(event):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].destroy()
            del canvas.data["drag_label"]
            block=canvas.data.get("drag_block")
            if block:
                canvas_x=canvas.winfo_pointerx()-canvas.winfo_rootx()-right_frame.winfo_x()
                canvas_y=canvas.winfo_pointery()-canvas.winfo_rooty()-right_frame.winfo_y()
                if 0<=canvas_x<=canvas.winfo_width() and 0<=canvas_y<=canvas.winfo_height():
                    name,generics,ports=block
                    if generics==[] and ports==[]:
                        messagebox.showinfo("Info",f"Block '{name}' has no generics or ports.")
                    else:
                        block_instance=EntityBlock(canvas,canvas_x,canvas_y,name,generics,ports,conduit=False)
                        canvas.data["blocks"].append(block_instance)
            del canvas.data["drag_block"]
            blocks_listbox.unbind("<Motion>")
            blocks_listbox.unbind("<ButtonRelease-1>")
    blocks_listbox.bind("<Button-1>",start_drag)
    def add_conduit(root,canvas):
        conduit_window=tk.Toplevel(root)
        conduit_window.title("New Conduit")
        tk.Label(conduit_window,text="Name:").pack(pady=2)
        name_entry=tk.Entry(conduit_window)
        name_entry.insert(0,"sig")
        name_entry.pack(pady=2)
        tk.Label(conduit_window,text="Direction:").pack(pady=2)
        direction_var=tk.StringVar(conduit_window,"in")
        tk.OptionMenu(conduit_window,direction_var,"in","out","inout").pack(pady=2)
        tk.Label(conduit_window,text="Bit width (leave blank for default):").pack(pady=2)
        width_entry=tk.Entry(conduit_window)
        width_entry.insert(0,"1")
        width_entry.pack(pady=2)
        tk.Label(conduit_window,text="Base Type (e.g., std_logic, integer):").pack(pady=2)
        type_entry=tk.Entry(conduit_window)
        type_entry.insert(0,"std_logic")
        type_entry.pack(pady=2)
        def create_conduit():
            name=name_entry.get().strip()
            direction=direction_var.get()
            width=width_entry.get().strip()
            base_type=type_entry.get().strip()
            if not name:
                messagebox.showerror("Input Error","Conduit name cannot be empty.")
                return
            for block in canvas.data["blocks"]:
                if hasattr(block,'conduit') and block.conduit and block.name==name:
                    messagebox.showerror("Duplicate Error",f"Conduit '{name}' already exists.")
                    return
            if width.isdigit():
                width=int(width)
                if width<=1:
                    if base_type.lower() in ["std_logic_vector","signed","unsigned","std_logic"]:
                        final_type="std_logic"
                    else:
                        final_type=base_type
                else:
                    if base_type.lower()=="std_logic":
                        final_type=f"std_logic_vector({width-1}:0)"
                    elif base_type.lower() in ["signed","unsigned","std_logic_vector"]:
                        final_type=f"{base_type}({width-1}:0)"
                    else:
                        final_type=base_type
            else:
                final_type=base_type
            conduit=EntityBlock(canvas,100,100,name,[],[{"name":name,"dir":direction,"type":final_type}],conduit=True)
            canvas.data["blocks"].append(conduit)
            conduit_window.destroy()
        tk.Button(conduit_window,text="Create",command=create_conduit).pack(pady=10)
    root.mainloop()
