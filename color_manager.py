#color_manager.py
class ColorManager:
    def __init__(self):
        self.colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd",
            "#8c564b", "#7f7f7f", "#bcbd22", "#17becf",
            "#aec7e8", "#98df8a", "#c5b0d5", "#c49c94",
            "#9edae5", "#ffbb78", "#c7c7c7", "#393b79"
        ]
        self.index = 0

    def get_next_color(self):
        c = self.colors[self.index % len(self.colors)]
        self.index += 1
        return c
