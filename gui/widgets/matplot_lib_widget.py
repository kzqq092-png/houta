from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


class MatplotlibWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(2, 2))
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_pie(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        from collections import Counter
        counter = Counter(data)
        labels, sizes = zip(*counter.items()) if counter else ([], [])
        if sizes:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title('类型分布')
        self.canvas.draw()

    def plot_bar(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        from collections import Counter
        counter = Counter(data)
        labels, sizes = zip(*sorted(counter.items())) if counter else ([], [])
        if sizes:
            ax.bar(labels, sizes)
        ax.set_title('价格区间分布')
        self.canvas.draw()
