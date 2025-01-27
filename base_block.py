import tkinter as tk

class DraggableBlock:
    def __init__(self,canvas,x,y):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.dragging = False
        self.ox = 0
        self.oy = 0

    def on_click(self,event):
        if not self.dragging:
            self.dragging = True
            self.ox = self.x - event.x
            self.oy = self.y - event.y
            self.canvas.bind("<B1-Motion>",self.on_drag)
            self.canvas.bind("<ButtonRelease-1>",self.on_release)

    def on_drag(self,event):
        if not self.dragging:
            return
        nx = event.x + self.ox
        ny = event.y + self.oy
        dx = nx - self.x
        dy = ny - self.y
        self.x = nx
        self.y = ny
        self.move_block(dx,dy)
        self.move_ports(dx,dy)
        self.update_connections()

    def on_release(self,event):
        self.dragging = False
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

    def move_block(self,dx,dy):
        pass

    def move_ports(self,dx,dy):
        pass

    def update_connections(self):
        pass

    def remove_port(self, port):
        cs = self.canvas.data["connections"]
        for c in cs[:]:
            if c[0] == port or c[1] == port:
                self.canvas.delete(c[2])
                cs.remove(c)
        self.canvas.delete(port.id)
        self.canvas.delete(port.label_id)
        if port.id in self.canvas.data["port_map"]:
            del self.canvas.data["port_map"][port.id]
        if port.label_id in self.canvas.data["port_map"]:
            del self.canvas.data["port_map"][port.label_id]

    def remove_all_connections(self):
        pass

    def rename_block(self,title):
        w = tk.Toplevel(self.canvas)
        w.title(title)
        tk.Label(w,text="New Name:").pack()
        e = tk.Entry(w)
        e.insert(0,self.name)
        e.pack()
        def ok():
            v = e.get().strip()
            if v:
                self.name = v
                self.canvas.itemconfig(self.text, text=v)
            w.destroy()
        tk.Button(w, text="OK", command=ok).pack()

    def update_curved_line(self,wire,port1,port2):
        sx, sy = port1.x, port1.y
        ex, ey = port2.x, port2.y
        cx1 = sx + (ex - sx)/2
        cy1 = sy
        cx2 = sx + (ex - sx)/2
        cy2 = ey
        self.canvas.coords(wire, sx, sy, cx1, cy1, cx2, cy2, ex, ey)
