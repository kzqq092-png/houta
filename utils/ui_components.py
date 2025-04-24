"""
UI Components Manager

This module provides utility classes for managing UI components.
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from utils.theme import Theme, ThemeManager

__all__ = ['Theme', 'ThemeManager']

class ChartManager:
    """Manages chart creation and updates"""
    
    @staticmethod
    def create_chart(parent=None):
        """Create a new chart widget"""
        figure = Figure()
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, parent)
        
        return figure, canvas, toolbar
    
    @staticmethod
    def update_chart_theme(figure, colors):
        """Update chart theme colors"""
        figure.patch.set_facecolor(colors['chart_background'])
        
        for ax in figure.axes:
            ax.set_facecolor(colors['chart_background'])
            ax.spines['bottom'].set_color(colors['text'])
            ax.spines['top'].set_color(colors['text'])
            ax.spines['left'].set_color(colors['text'])
            ax.spines['right'].set_color(colors['text'])
            ax.tick_params(axis='x', colors=colors['text'])
            ax.tick_params(axis='y', colors=colors['text'])
            ax.xaxis.label.set_color(colors['text'])
            ax.yaxis.label.set_color(colors['text'])
            ax.title.set_color(colors['text'])
            ax.grid(True, color=colors['grid'], alpha=0.3)

class WidgetFactory:
    """Factory class for creating common widgets"""
    
    @staticmethod
    def create_group_box(title, layout=None):
        """Create a QGroupBox with optional layout"""
        group = QGroupBox(title)
        if layout:
            group.setLayout(layout)
        return group
    
    @staticmethod
    def create_form_row(label_text, widget):
        """Create a form row with label and widget"""
        layout = QHBoxLayout()
        label = QLabel(label_text)
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout
    
    @staticmethod
    def create_spin_box(min_val, max_val, default=0, step=1):
        """Create a QSpinBox with specified parameters"""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        return spin
    
    @staticmethod
    def create_double_spin_box(min_val, max_val, default=0.0, decimals=2):
        """Create a QDoubleSpinBox with specified parameters"""
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setDecimals(decimals)
        return spin 