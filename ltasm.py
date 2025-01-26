import os
import re
import sys
import tkinter as tk
from tkinter import filedialog

DEBUG=True

def preprocess_vhdl(text):
    lines=text.split('\n')
    out=[]
    for line in lines:
        idx=line.find('--')
        if idx!=-1:
            line=line[:idx]
        out.append(line)
    # remove any leftover inline comments, unify whitespace
    return '\n'.join(out)

def extract_ports(block):
    block=block.strip()
    # remove newlines
    block=block.replace('\n',' ').replace('\r',' ')
    # The last port may not have a trailing semicolon if the user omitted it,
    # so let's ensure we have one at the end so splitting is consistent
    if not block.endswith(';'):
        block+=';'
    items=re.split(r';',block)
    ports=[]
    for item in items:
        item=item.strip()
        if not item:
            continue
        # pattern: name : in|out|inout <type>
        m=re.match(r"([\w\d_]+)\s*:\s*(in|out|inout)\s+(.+)$",item,re.IGNORECASE)
        if m:
            nm=m.group(1).strip()
            dr=m.group(2).lower().strip()
            tp=m.group(3).strip().rstrip(',')
            ports.append({"name":nm,"dir":dr,"type":tp})
    return ports

def parse_vhdl_for_entities(text):
    text = preprocess_vhdl(text)
    entity_pattern = r"entity\s+([\w\d_]+)\s+is\s+(.*?)end\s+\1\s*;"
    found = re.findall(entity_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    out = []
    
    for enName, enBody in found:
        port_pattern = r"port\s*\(\s*(.*)\s*\)\s*;"
        pm = re.search(port_pattern, enBody, flags=re.DOTALL | re.IGNORECASE)
        ports = []
        
        if pm:
            block = pm.group(1)
            print(block)  # For debugging purposes
            ports = extract_ports(block)
        
        out.append((enName, ports))
    
    return out


def scan_file(path):
    if DEBUG: print("Scanning file:", path)
    with open(path,"r") as f:
        c=f.read()
    return parse_vhdl_for_entities(c)

def find_entities(d):
    if DEBUG: print("Finding entities in directory:", d)
    ents=[]
    if not os.path.isdir(d):
        return ents
    for f in os.listdir(d):
        lf=f.lower()
        if (lf.endswith(".vhd") or lf.endswith(".vhdl")) and not lf.startswith("tb_") and not lf.endswith("_tb.vhd") and not lf.endswith("_tb.vhdl"):
            p=os.path.join(d,f)
            parsed=scan_file(p)
            ents.extend(parsed)
    ip=os.path.join(d,"ip")
    if os.path.isdir(ip):
        for r,dirs,files in os.walk(ip):
            for f in files:
                lf=f.lower()
                if (lf.endswith(".vhd") or lf.endswith(".vhdl")) and not lf.startswith("tb_") and not lf.endswith("_tb.vhd") and not lf.endswith("_tb.vhdl"):
                    p=os.path.join(r,f)
                    parsed=scan_file(p)
                    ents.extend(parsed)
    return ents

def parse_vhdl_range(s):
    m=re.search(r"\((\d+)\s*downto\s*0\)",s,re.IGNORECASE)
    if m:
        try: return int(m.group(1))+1
        except: return None
    return None

def extract_width(vtype):
    st=vtype.lower().strip()
    if "std_logic" in st:
        if "vector" in st:
            w=parse_vhdl_range(st)
            return w if w else None
        else:
            return 1
    if "signed" in st or "unsigned" in st:
        w=parse_vhdl_range(st)
        return w if w else None
    if "integer" in st:
        return None
    return None

def extract_kind(vtype):
    s=vtype.lower().strip()
    if "std_logic" in s:
        if "vector" in s:
            return "SLV"
        else:
            return "SL"
    if "signed" in s:
        return "SIGNED"
    if "unsigned" in s:
        return "UNSIGNED"
    if "integer" in s:
        return "INTEGER"
    return "OTHER"

def check_dir(d1,d2):
    if d1=="out" and d2 in ["in","inout"]: return True
    if d1=="in" and d2 in ["out","inout"]: return True
    if d1=="inout" and d2 in ["in","out","inout"]: return True
    return False

def types_compatible(a,b):
    if a["kind"]==b["kind"]:
        if a["kind"] in ["SL","OTHER"]:
            return True
        if a["kind"] in ["SLV","SIGNED","UNSIGNED"]:
            if a["width"]==None or b["width"]==None:
                return False
            return a["width"]==b["width"]
        if a["kind"]=="INTEGER":
            return True
    return False

class PortSymbol:
    def __init__(self,canvas,x,y,block,port):
        self.canvas=canvas
        self.x=x
        self.y=y
        self.block=block
        self.port=port
        self.meta={"kind":extract_kind(port["type"]),"width":extract_width(port["type"])}
        if DEBUG:
            print("Creating port symbol:", port["name"], "type:",port["type"], "kind:",self.meta["kind"],"width:", self.meta["width"])
        wval=self.meta["width"]
        # single bit => circle
        # else => square
        useSquare=True
        if self.meta["kind"]=="SL" and wval==1:
            useSquare=False
        self.shape="square" if useSquare else "circle"
        if self.shape=="circle":
            self.r=5
            self.id=self.canvas.create_oval(self.x-self.r,self.y-self.r,self.x+self.r,self.y+self.r,fill="white")
        else:
            s=10
            self.r=s/2
            self.id=self.canvas.create_rectangle(self.x-self.r,self.y-self.r,self.x+self.r,self.y+self.r,fill="white")

        disp=port["name"]
        if wval and wval>1:
            disp+="["+str(wval)+"]"
        off=-5 if port["dir"] in ["in","inout"] else 5
        anc="e" if off<0 else "w"
        self.label_id=self.canvas.create_text(self.x+off,self.y,text=disp,anchor=anc)
        self.canvas.tag_bind(self.id,"<ButtonPress-1>",self.on_press)
        self.canvas.tag_bind(self.id,"<B1-Motion>",self.on_drag)
        self.canvas.tag_bind(self.id,"<ButtonRelease-1>",self.on_release)
        self.dragging=False

    def on_press(self,e):
        self.dragging=True
        if self.canvas.data["active_line"] is None:
            l=self.canvas.create_line(self.x,self.y,self.x,self.y,fill="black")
            self.canvas.data["active_line"]=l
            self.canvas.data["active_port"]=self

    def on_drag(self,e):
        if self.dragging and self.canvas.data["active_line"] is not None:
            self.canvas.coords(self.canvas.data["active_line"],self.x,self.y,e.x,e.y)

    def on_release(self,e):
        if not self.dragging:
            return
        self.dragging=False
        line=self.canvas.data["active_line"]
        sp=self.canvas.data["active_port"]
        if sp and line:
            ids=self.canvas.find_overlapping(e.x,e.y,e.x,e.y)
            done=False
            for i in ids:
                if i!=self.id and i in self.canvas.data["port_map"]:
                    cp=self.canvas.data["port_map"][i]
                    if cp!=sp and check_dir(sp.port["dir"],cp.port["dir"]):
                        a=sp.meta
                        b=cp.meta
                        if types_compatible(a,b):
                            self.canvas.coords(line,sp.x,sp.y,cp.x,cp.y)
                            self.canvas.data["connections"].append((sp,cp,line,None))
                            done=True
                            break
                        else:
                            mx=(sp.x+cp.x)/2
                            my=(sp.y+cp.y)/2
                            def pick_adapter(mode):
                                self.canvas.data["adapter_win"]=None
                                w.destroy()
                                self.canvas.delete(line)
                                ab=AdapterBlock(self.canvas,mx,my,a,b,mode)
                                self.canvas.data["blocks"].append(ab)
                                l1=self.canvas.create_line(sp.x,sp.y,ab.left_port.x,ab.left_port.y,fill="black")
                                self.canvas.data["connections"].append((sp,ab.left_port,l1,ab))
                                l2=self.canvas.create_line(ab.right_port.x,ab.right_port.y,cp.x,cp.y,fill="black")
                                self.canvas.data["connections"].append((ab.right_port,cp,l2,ab))
                            w=tk.Toplevel(self.canvas)
                            tk.Label(w,text="Type/Width mismatch. Adapter?").pack()
                            v=tk.StringVar(w,"Convert")
                            r1=tk.Radiobutton(w,text="Convert",variable=v,value="Convert")
                            r2=tk.Radiobutton(w,text="TruncateOrExtend",variable=v,value="TruncateOrExtend")
                            r1.pack()
                            r2.pack()
                            tk.Button(w,text="OK",command=lambda:pick_adapter(v.get())).pack()
                            done=True
                            break
            if not done:
                self.canvas.delete(line)
        self.canvas.data["active_line"]=None
        self.canvas.data["active_port"]=None

class AdapterBlock:
    def __init__(self,canvas,x,y,metaA,metaB,mode):
        self.canvas=canvas
        self.name="Adapter"
        self.x=x
        self.y=y
        self.dragging=False
        self.ox=0
        self.oy=0
        sz=25
        self.obj=self.canvas.create_polygon(self.x,self.y-sz,self.x-sz,self.y,self.x,self.y+sz,self.x+sz,self.y,fill="pink")
        self.text=self.canvas.create_text(self.x,self.y,text="Adapter",font=("Arial",10))
        self.canvas.tag_bind(self.obj,"<Button-1>",self.on_click)
        self.canvas.tag_bind(self.text,"<Button-1>",self.on_click)
        self.menu=tk.Menu(self.canvas,tearoff=0)
        self.menu.add_command(label="Delete",command=self.delete_self)
        self.menu.add_command(label="Rename",command=self.rename_self)
        self.menu.add_command(label="Edit Adapter",command=self.edit_adapter)
        self.canvas.tag_bind(self.obj,"<Button-3>",self.on_right_click)
        self.canvas.tag_bind(self.text,"<Button-3>",self.on_right_click)

        self.metaA=metaA
        self.metaB=metaB
        self.mode=mode

        ist="std_logic"
        ost="std_logic"
        wA=metaA["width"]
        kA=metaA["kind"]
        if kA in ["SLV","SIGNED","UNSIGNED"] and wA:
            if kA=="SLV":
                ist="std_logic_vector({} downto 0)".format(wA-1) if wA>1 else "std_logic"
            else:
                ist=f"{kA.lower()}({wA-1} downto 0)" if wA>1 else kA.lower()+"(0 downto 0)"
        elif kA=="INTEGER":
            ist="integer"

        wB=metaB["width"]
        kB=metaB["kind"]
        if kB in ["SLV","SIGNED","UNSIGNED"] and wB:
            if kB=="SLV":
                ost="std_logic_vector({} downto 0)".format(wB-1) if wB>1 else "std_logic"
            else:
                ost=f"{kB.lower()}({wB-1} downto 0)" if wB>1 else kB.lower()+"(0 downto 0)"
        elif kB=="INTEGER":
            ost="integer"

        self.left_port=PortSymbol(self.canvas,self.x-30,self.y,self,{"name":"Din","dir":"in","type":ist})
        self.right_port=PortSymbol(self.canvas,self.x+30,self.y,self,{"name":"Dout","dir":"out","type":ost})
        self.canvas.data["port_map"][self.left_port.id]=self.left_port
        self.canvas.data["port_map"][self.left_port.label_id]=self.left_port
        self.canvas.data["port_map"][self.right_port.id]=self.right_port
        self.canvas.data["port_map"][self.right_port.label_id]=self.right_port

    def on_right_click(self,e):
        self.menu.post(e.x_root,e.y_root)

    def delete_self(self):
        for c in [self.left_port,self.right_port]:
            for co in self.canvas.data["connections"][:]:
                if co[0]==c or co[1]==c:
                    self.canvas.delete(co[2])
                    self.canvas.data["connections"].remove(co)
            self.canvas.delete(c.id)
            self.canvas.delete(c.label_id)
            if c.id in self.canvas.data["port_map"]:
                del self.canvas.data["port_map"][c.id]
            if c.label_id in self.canvas.data["port_map"]:
                del self.canvas.data["port_map"][c.label_id]
        self.canvas.delete(self.obj)
        self.canvas.delete(self.text)
        if self in self.canvas.data["blocks"]:
            self.canvas.data["blocks"].remove(self)

    def rename_self(self):
        w=tk.Toplevel(self.canvas)
        l=tk.Label(w,text="New Name:")
        l.pack()
        e=tk.Entry(w)
        e.insert(0,self.name)
        e.pack()
        def done():
            nm=e.get()
            self.name=nm
            self.canvas.itemconfig(self.text,text=nm)
            w.destroy()
        b=tk.Button(w,text="OK",command=done)
        b.pack()

    def edit_adapter(self):
        w=tk.Toplevel(self.canvas)
        l=tk.Label(w,text="Edit Adapter Properties (No real effect yet)")
        l.pack()
        e=tk.Entry(w)
        e.insert(0,self.mode)
        e.pack()
        def done():
            self.mode=e.get()
            w.destroy()
        b=tk.Button(w,text="OK",command=done)
        b.pack()

    def on_click(self,e):
        if not self.dragging:
            self.dragging=True
            c=self.canvas.coords(self.obj)
            cx=(c[0]+c[4])/2
            cy=(c[1]+c[5])/2
            self.ox=cx-e.x
            self.oy=cy-e.y
            self.canvas.bind("<B1-Motion>",self.on_drag)
            self.canvas.bind("<ButtonRelease-1>",self.on_release)

    def on_drag(self,e):
        if not self.dragging:
            return
        dx=e.x+self.ox-self.x
        dy=e.y+self.oy-self.y
        self.x=e.x+self.ox
        self.y=e.y+self.oy
        self.canvas.move(self.obj,dx,dy)
        self.canvas.move(self.text,dx,dy)
        for c in [self.left_port,self.right_port]:
            c.x+=dx
            c.y+=dy
            if c.shape=="circle":
                self.canvas.coords(c.id,c.x-c.r,c.y-c.r,c.x+c.r,c.y+c.r)
            else:
                self.canvas.coords(c.id,c.x-c.r,c.y-c.r,c.x+c.r,c.y+c.r)
            self.canvas.coords(c.label_id,c.x+(-5 if c.port["dir"] in ["in","inout"] else 5),c.y)
            for co in self.canvas.data["connections"]:
                if co[0]==c or co[1]==c:
                    if co[0]==c:
                        ox,oy=co[1].x,co[1].y
                        self.canvas.coords(co[2],c.x,c.y,ox,oy)
                    else:
                        ox,oy=co[0].x,co[0].y
                        self.canvas.coords(co[2],ox,oy,c.x,c.y)

    def on_release(self,e):
        self.dragging=False
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

class EntityBlock:
    def __init__(self,canvas,x,y,name,ports,conduit=False):
        self.canvas=canvas
        self.name=name
        self.ports=ports
        self.conduit=conduit
        lines=[name]+[p["dir"]+" "+p["name"] for p in ports]
        mx=max(len(s) for s in lines) if lines else 10
        self.w=10*mx
        self.h=40+len(ports)*20
        if self.h<60:
            self.h=60
        fc="lightyellow" if conduit else "lightblue"
        self.obj=self.canvas.create_rectangle(x,y,x+self.w,y+self.h,fill=fc)
        self.title_id=self.canvas.create_text(x+5,y+5,anchor="nw",text=name,font=("Arial",10))
        self.x=x
        self.y=y
        self.dragging=False
        self.ox=0
        self.oy=0
        self.menu=tk.Menu(self.canvas,tearoff=0)
        self.menu.add_command(label="Delete",command=self.delete_self)
        if conduit:
            self.menu.add_command(label="Rename",command=self.rename_self)
        self.canvas.tag_bind(self.obj,"<Button-3>",self.on_right_click)
        self.canvas.tag_bind(self.title_id,"<Button-3>",self.on_right_click)
        self.canvas.tag_bind(self.obj,"<Button-1>",self.on_click)
        self.canvas.tag_bind(self.title_id,"<Button-1>",self.on_click)
        self.port_symbols=[]
        lc=0
        rc=0
        py0=y+40
        for p in ports:
            if p["dir"] in ["in","inout"]:
                px=x
                py=py0+lc*20
                lc+=1
            else:
                px=x+self.w
                py=py0+rc*20
                rc+=1
            ps=PortSymbol(self.canvas,px,py,self,p)
            self.canvas.data["port_map"][ps.id]=ps
            self.canvas.data["port_map"][ps.label_id]=ps
            self.port_symbols.append(ps)

    def on_right_click(self,e):
        self.menu.post(e.x_root,e.y_root)

    def delete_self(self):
        for c in self.port_symbols:
            for co in self.canvas.data["connections"][:]:
                if co[0]==c or co[1]==c:
                    self.canvas.delete(co[2])
                    self.canvas.data["connections"].remove(co)
            self.canvas.delete(c.id)
            self.canvas.delete(c.label_id)
            if c.id in self.canvas.data["port_map"]:
                del self.canvas.data["port_map"][c.id]
            if c.label_id in self.canvas.data["port_map"]:
                del self.canvas.data["port_map"][c.label_id]
        self.canvas.delete(self.obj)
        self.canvas.delete(self.title_id)
        if self in self.canvas.data["blocks"]:
            self.canvas.data["blocks"].remove(self)

    def rename_self(self):
        w=tk.Toplevel(self.canvas)
        l=tk.Label(w,text="New Name:")
        l.pack()
        e=tk.Entry(w)
        e.insert(0,self.name)
        e.pack()
        def done():
            nn=e.get()
            self.name=nn
            self.canvas.itemconfig(self.title_id,text=nn)
            w.destroy()
        b=tk.Button(w,text="OK",command=done)
        b.pack()

    def on_click(self,e):
        if not self.dragging:
            self.dragging=True
            self.ox=self.canvas.coords(self.obj)[0]-e.x
            self.oy=self.canvas.coords(self.obj)[1]-e.y
            self.canvas.bind("<B1-Motion>",self.on_drag)
            self.canvas.bind("<ButtonRelease-1>",self.on_release)

    def on_drag(self,e):
        if not self.dragging:
            return
        nx=e.x+self.ox
        ny=e.y+self.oy
        self.canvas.coords(self.obj,nx,ny,nx+self.w,ny+self.h)
        self.canvas.coords(self.title_id,nx+5,ny+5)
        dx=nx-self.x
        dy=ny-self.y
        self.x=nx
        self.y=ny
        for c in self.port_symbols:
            c.x+=dx
            c.y+=dy
            if c.shape=="circle":
                self.canvas.coords(c.id,c.x-c.r,c.y-c.r,c.x+c.r,c.y+c.r)
            else:
                self.canvas.coords(c.id,c.x-c.r,c.y-c.r,c.x+c.r,c.y+c.r)
            self.canvas.coords(c.label_id,c.x+(-5 if c.port["dir"] in ["in","inout"] else 5),c.y)
            for co in self.canvas.data["connections"]:
                if co[0]==c or co[1]==c:
                    if co[0]==c:
                        ox,oy=co[1].x,co[1].y
                        self.canvas.coords(co[2],c.x,c.y,ox,oy)
                    else:
                        ox,oy=co[0].x,co[0].y
                        self.canvas.coords(co[2],ox,oy,c.x,c.y)

    def on_release(self,e):
        self.dragging=False
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

def generate_top_level(canvas):
    if not os.path.exists("Adapters"):
        os.mkdir("Adapters")
    with open(os.path.join("Adapters","TopLevelAdapter.vhd"),"w") as f:
        f.write("library ieee;\nuse ieee.std_logic_1164.all;\nuse ieee.numeric_std.all;\nentity TopLevelAdapter is\nport(\n")
        conduit=[]
        comps={}
        blocks=[]
        for b in canvas.data["blocks"]:
            blocks.append(b)
            if b.conduit:
                for p in b.ports:
                    conduit.append((b.name,p["dir"],p["type"]))
            else:
                if b.name not in comps:
                    comps[b.name]=b.ports
        ccount=len(conduit)
        for i in range(ccount):
            nm,dr,ty=conduit[i]
            s=nm+" : "+dr+" "+ty
            if i<ccount-1:
                s+=";"
            f.write(s+"\n")
        if ccount==0:
            f.write("clk : in std_logic;\nreset : in std_logic;\nconduit_in : in std_logic_vector(31 downto 0);\nconduit_out : out std_logic_vector(31 downto 0)\n")
        f.write(");\nend TopLevelAdapter;\narchitecture rtl of TopLevelAdapter is\n")
        for k in comps:
            f.write("component "+k+" is\n")
            p=comps[k]
            if p:
                f.write("port(\n")
                for i in range(len(p)):
                    ss=p[i]["name"]+" : "+p[i]["dir"]+" "+p[i]["type"]
                    if i<len(p)-1:
                        ss+=";"
                    f.write(ss+"\n")
                f.write(");\n")
            f.write("end component;\n")
        f.write("begin\n")
        ic={}
        for b in blocks:
            if b.conduit:
                continue
            if b.name not in ic:
                ic[b.name]=0
            idx=ic[b.name]
            ic[b.name]+=1
            nm=b.name+"_inst"+str(idx)
            f.write(nm+": "+b.name+" port map(\n);\n")
        f.write("end rtl;\n")

def run_gui(d):
    es=find_entities(d)
    root=tk.Tk()
    root.title("Efinix System Builder")
    lf=tk.Frame(root)
    lf.pack(side="left",fill="y")
    rf=tk.Frame(root)
    rf.pack(side="right",expand=True,fill="both")
    lb=tk.Listbox(lf)
    lb.pack(side="top",fill="both",expand=True)
    for e in es:
        lb.insert("end",e[0])
    c=tk.Canvas(rf,bg="white")
    c.pack(side="top",expand=True,fill="both")
    c.data={"connections":[],"blocks":[],"port_map":{},"active_line":None,"active_port":None}

    def sd(e):
        idx=lb.curselection()
        if idx:
            nm=lb.get(idx)
            ent=None
            for ee in es:
                if ee[0]==nm:
                    ent=ee
                    break
            if ent:
                c.data["drag_entity"]=ent
                c.data["drag_obj"]=tk.Label(lf,text=nm,bg="lightgreen")
                c.data["drag_obj"].place(x=e.x,y=e.y)
                lb.bind("<Motion>",dd)
                lb.bind("<ButtonRelease-1>",ed)

    def dd(e):
        if "drag_obj" in c.data:
            c.data["drag_obj"].place(x=e.x,y=e.y)

    def ed(e):
        if "drag_obj" in c.data:
            xx=root.winfo_pointerx()-c.winfo_rootx()
            yy=root.winfo_pointery()-c.winfo_rooty()
            if 0<=xx<=c.winfo_width() and 0<=yy<=c.winfo_height():
                ent=c.data["drag_entity"]
                blk=EntityBlock(c,xx,yy,ent[0],ent[1],False)
                c.data["blocks"].append(blk)
            c.data["drag_obj"].destroy()
            del c.data["drag_obj"]
            del c.data["drag_entity"]
        lb.unbind("<Motion>")
        lb.unbind("<ButtonRelease-1>")

    lb.bind("<Button-1>",sd)

    def add_conduit():
        w=tk.Toplevel(root)
        w.title("New Conduit")
        nl=tk.Label(w,text="Name:")
        nl.pack()
        ne=tk.Entry(w)
        ne.insert(0,"sig")
        ne.pack()
        dl=tk.Label(w,text="Direction:")
        dl.pack()
        ddv=tk.StringVar(w)
        ddv.set("in")
        om=tk.OptionMenu(w,ddv,"in","out","inout")
        om.pack()
        wl=tk.Label(w,text="Bit width (leave blank for e.g. integer or unknown):")
        wl.pack()
        we=tk.Entry(w)
        we.insert(0,"1")
        we.pack()
        tl=tk.Label(w,text="Base Type (std_logic_vector, integer, signed, unsigned, std_logic, etc.):")
        tl.pack()
        te=tk.Entry(w)
        te.insert(0,"std_logic")
        te.pack()
        def ok():
            n=ne.get()
            for b in c.data["blocks"]:
                if b.conduit and b.name==n:
                    e2=tk.Toplevel(w)
                    l2=tk.Label(e2,text="Conduit with that name already exists")
                    l2.pack()
                    return
            d=ddv.get()
            width=we.get().strip()
            btype=te.get().strip()
            if width.isdigit():
                wi=int(width)
                if wi<=1:
                    if btype.lower() in ["std_logic_vector","signed","unsigned"]:
                        t="std_logic"
                    else:
                        t=btype
                else:
                    if btype.lower() in ["signed","unsigned","std_logic_vector"]:
                        t=btype+"({} downto 0)".format(wi-1)
                    else:
                        t=btype
            else:
                t=btype
            block=EntityBlock(c,100,100,n,[{"name":n,"dir":d,"type":t}],True)
            c.data["blocks"].append(block)
            w.destroy()
        b=tk.Button(w,text="OK",command=ok)
        b.pack()

    ac=tk.Button(lf,text="New Conduit",command=add_conduit)
    ac.pack(side="top",fill="x")

    gb=tk.Button(lf,text="Generate TopLevel",command=lambda:generate_top_level(c))
    gb.pack(side="bottom",fill="x")

    root.mainloop()

if __name__=="__main__":
    if len(sys.argv)>1:
        d=sys.argv[1]
    else:
        d=filedialog.askdirectory()
    run_gui(d)