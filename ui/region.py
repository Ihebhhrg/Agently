from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen

class RegionSelector(QWidget):
    selected = Signal(int, int, int, int)
    
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)
        self.start = None
        self.end = None
        self.dragging = False
        self.hide()
    
    def showEvent(self, e):
        self.start = None
        self.end = None
        self.dragging = False
        self.update()
    
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.start = e.globalPosition().toPoint()
            self.dragging = True
        if e.button() == Qt.RightButton:
            self.hide()
    
    def mouseMoveEvent(self, e):
        if self.dragging and self.start:
            self.end = e.globalPosition().toPoint()
            self.update()
    
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            if self.start and self.end:
                x = min(self.start.x(), self.end.x())
                y = min(self.start.y(), self.end.y())
                w = abs(self.end.x()-self.start.x())
                h = abs(self.end.y()-self.start.y())
                if w > 5 and h > 5:
                    self.selected.emit(x,y,w,h)
            self.hide()
    
    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setBrush(QColor(0,0,0,100))
        painter.drawRect(self.rect())
        if self.start and self.end and self.dragging:
            x = min(self.start.x(), self.end.x())
            y = min(self.start.y(), self.end.y())
            w = abs(self.end.x()-self.start.x())
            h = abs(self.end.y()-self.start.y())
            painter.setBrush(QColor(0,0,0,0))
            pen = QPen(QColor(255,255,255,220))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(x,y,w,h)
