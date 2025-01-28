#color_manager.py
class ColorManager:
    def __init__(self):
        self.colors = [
            "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
            "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"
        ]
        self.index = 0
    def get_next_color(self):
        c = self.colors[self.index % len(self.colors)]
        self.index += 1
        return c
