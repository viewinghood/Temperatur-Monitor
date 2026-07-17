# -*- coding: utf-8 -*-
"""
PyQtGraph plot rendered off-screen, shown as a Kivy texture.

Each active trace gets its own stacked subplot with independent Y auto-scaling
and a shared linked time (X) axis. Updates are queued to a worker thread;
texture refresh is throttled on the Kivy main thread (no blocking wait).
"""

import os
import queue
import threading

import numpy as np

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget

TRACE_ORDER = ('TC1', 'TC2', 'TC3', 'TC4', 'U1 CJC', 'U2 CJC')
RENDER_INTERVAL_S = 0.2


class _PyQtGraphRendererThread(threading.Thread):
    CMD_UPDATE = 'update'
    CMD_RENDER = 'render'
    CMD_QUIT = 'quit'

    def __init__(self):
        super(_PyQtGraphRendererThread, self).__init__()
        self.daemon = True
        self._requests = queue.Queue()
        self._responses = queue.Queue()
        self._ready = threading.Event()
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._layout = None
        self._rows = {}
        self._active_names = []

    def run(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        import pyqtgraph as pg
        from PyQt5 import QtCore, QtGui, QtWidgets

        pg.setConfigOptions(antialias=False, background='#1a1a2e', foreground='#eaeaea')
        # useOpenGL=False — QT_QPA_PLATFORM=offscreen has no GL context on Pi.
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])

        self._layout = pg.GraphicsLayoutWidget()
        self._layout.setBackground('#1a1a2e')
        self._layout.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)
        self._layout.hide()

        self._ready.set()

        while True:
            try:
                cmd = self._requests.get(timeout=0.03)
            except queue.Empty:
                app.processEvents()
                continue

            op = cmd[0]
            if op == self.CMD_QUIT:
                break
            if op == self.CMD_UPDATE:
                self._apply_update(cmd[1], cmd[2], cmd[3], cmd[4] if len(cmd) > 4 else None)
                self._responses.put(True)
            elif op == self.CMD_RENDER:
                width, height = cmd[1], cmd[2]
                frame = self._grab_frame(app, width, height)
                with self._frame_lock:
                    self._latest_frame = frame
                self._responses.put(frame is not None)

        self._layout.close()

    def _grab_frame(self, app, width, height):
        from PyQt5 import QtGui

        if not self._active_names:
            return None
        self._layout.resize(max(120, int(width)), max(100, int(height)))
        app.processEvents()
        pix = self._layout.grab()
        image = pix.toImage().convertToFormat(QtGui.QImage.Format_RGBA8888)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        return np.frombuffer(ptr, np.uint8).reshape(
            (image.height(), image.width(), 4)).copy()

    def _apply_update(self, active_names, series, colors, x_range=None):
        import pyqtgraph as pg

        names = [n for n in TRACE_ORDER if n in active_names]
        if names != self._active_names:
            self._rebuild_layout(names, colors)
        elif not names:
            self._rows = {}
            self._layout.clear()
            self._active_names = []
            return

        x_max = 1.0
        for name in names:
            x, y = series.get(name, ([], []))
            x = np.asarray(x, dtype=np.float64)
            y = np.asarray(y, dtype=np.float64)
            if x.size == 1:
                x = np.array([x[0], x[0] + 0.01], dtype=np.float64)
                y = np.array([y[0], y[0]], dtype=np.float64)
            row = self._rows[name]
            row['curve'].setData(x, y)
            vb = row['plot'].getViewBox()
            if y.size > 0:
                y_min = float(np.min(y))
                y_max = float(np.max(y))
                span = y_max - y_min
                if span <= 2.0:
                    mean = float(np.mean(y))
                    vb.setYRange(mean - 1.0, mean + 1.0, padding=0.02)
                else:
                    pad = max(0.5, span * 0.05)
                    vb.setYRange(y_min - pad, y_max + pad, padding=0.02)
            elif name.endswith('CJC'):
                vb.setYRange(20.0, 50.0, padding=0.02)
            else:
                vb.setYRange(0.0, 120.0, padding=0.02)
            if x.size:
                x_max = max(x_max, float(x[-1]))

        if x_range is not None:
            x0, x1 = x_range
        else:
            x0, x1 = 0.0, max(5.0, x_max)
        for name in names:
            self._rows[name]['plot'].getViewBox().setXRange(x0, x1, padding=0.02)

    def _rebuild_layout(self, names, colors):
        import pyqtgraph as pg

        self._layout.clear()
        self._rows = {}
        self._active_names = list(names)
        if not names:
            return

        first_plot = None
        for i, name in enumerate(names):
            plot = self._layout.addPlot(row=i, col=0)
            plot.showAxis('top', False)
            plot.showAxis('right', False)
            plot.setMenuEnabled(False)
            plot.getViewBox().setMouseEnabled(x=False, y=False)
            pen_color = colors.get(name, '#eaeaea')
            plot.setLabel('left', name, color=pen_color)
            if i < len(names) - 1:
                plot.hideAxis('bottom')
            else:
                plot.setLabel('bottom', 'Zeit (s)')
            curve = plot.plot([], [], pen=pg.mkPen(color=pen_color, width=2))
            self._rows[name] = {'plot': plot, 'curve': curve}
            if first_plot is None:
                first_plot = plot
            else:
                plot.setXLink(first_plot)

    def wait_ready(self, timeout=15.0):
        return self._ready.wait(timeout)

    def request(self, *args, wait=False, timeout=5.0):
        self._requests.put(args)
        if wait:
            return self._responses.get(timeout=timeout)

    def pop_frame(self):
        with self._frame_lock:
            frame = self._latest_frame
            self._latest_frame = None
        return frame


class PyQtGraphPlotWidget(Widget):
    """Kivy widget displaying stacked PyQtGraph traces."""

    def __init__(self, **kwargs):
        super(PyQtGraphPlotWidget, self).__init__(**kwargs)
        self._renderer = _PyQtGraphRendererThread()
        self._renderer.start()
        if not self._renderer.wait_ready():
            raise RuntimeError('PyQtGraph renderer thread failed to start')

        self._texture = Texture.create(size=(1, 1), colorfmt='rgba')
        self._texture.flip_vertical()
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=self._texture, pos=self.pos, size=self.size)

        self.bind(pos=self._sync_rect, size=self._on_size)
        self._t0 = None
        self._series_data = {}
        self._active_names = []
        self._colors = {}
        self._view_x = None
        self._auto_x = True
        self._pan_anchor = None
        self._render_ev = None

        Clock.schedule_once(lambda _dt: self._schedule_render(force=True), 0.5)
        Clock.schedule_interval(self._poll_frame, RENDER_INTERVAL_S)

    def on_parent(self, widget, parent):
        if parent is None:
            self._shutdown()

    def _shutdown(self):
        if self._render_ev is not None:
            self._render_ev.cancel()
        if self._renderer.is_alive():
            self._renderer.request(self._renderer.CMD_QUIT)

    def _sync_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _on_size(self, *args):
        self._sync_rect()
        self._schedule_render(force=True)

    def clear_series(self):
        self._series_data = {}
        self._active_names = []
        self._t0 = None
        self._auto_x = True
        self._view_x = None
        self._renderer.request(
            self._renderer.CMD_UPDATE, [], {}, {}, None, wait=False)
        self._schedule_render(force=True)

    def set_series_snapshot(self, series_dict, t0=None, colors=None):
        """series_dict: {name: [(unix_t, value), ...]}"""
        if colors:
            self._colors = dict(colors)
        if t0 is not None:
            self._t0 = t0
        if self._t0 is None and series_dict:
            for points in series_dict.values():
                if points:
                    self._t0 = points[0][0]
                    break
        if self._t0 is None:
            return

        self._active_names = [n for n in TRACE_ORDER if n in series_dict]
        self._series_data = {}
        pg_series = {}
        for name, points in series_dict.items():
            xs = []
            ys = []
            for ts, val in points:
                if val is None:
                    continue
                xs.append(ts - self._t0)
                ys.append(val)
            self._series_data[name] = (xs, ys)
            pg_series[name] = (xs, ys)

        x_range = None if self._auto_x else self._view_x
        self._renderer.request(
            self._renderer.CMD_UPDATE,
            self._active_names, pg_series, self._colors, x_range, wait=False)
        self._schedule_render()

    def _schedule_render(self, force=False):
        if force and self._render_ev is not None:
            self._render_ev.cancel()
            self._render_ev = None
        if self._render_ev is None:
            self._render_ev = Clock.schedule_once(self._request_render, 0)

    def _request_render(self, _dt):
        self._render_ev = None
        if self.width < 2 or self.height < 2:
            return
        self._renderer.request(
            self._renderer.CMD_RENDER, self.width, self.height, wait=False)

    def _poll_frame(self, _dt):
        frame = self._renderer.pop_frame()
        if frame is None or frame.size == 0:
            return
        h, w = frame.shape[:2]
        if self._texture.size[0] != w or self._texture.size[1] != h:
            self._texture = Texture.create(size=(w, h), colorfmt='rgba')
            self._texture.flip_vertical()
            self._rect.texture = self._texture
        self._texture.blit_buffer(frame.tobytes(), colorfmt='rgba', bufferfmt='ubyte')

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super(PyQtGraphPlotWidget, self).on_touch_down(touch)
        if hasattr(touch, 'is_mouse_scrolling') and touch.is_mouse_scrolling:
            if touch.button == 'scrolldown':
                self._zoom(1.15, touch.x)
            elif touch.button == 'scrollup':
                self._zoom(1.0 / 1.15, touch.x)
            return True
        if touch.is_double_tap:
            self._auto_x = True
            self._view_x = None
            self._schedule_render(force=True)
            return True
        touch.grab(self)
        self._pan_anchor = (touch.x, touch.y)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super(PyQtGraphPlotWidget, self).on_touch_move(touch)
        if self._pan_anchor is None:
            return True
        dx = touch.x - self._pan_anchor[0]
        self._pan_anchor = (touch.x, touch.y)
        self._auto_x = False
        self._pan_pixels(dx)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._pan_anchor = None
            return True
        return super(PyQtGraphPlotWidget, self).on_touch_up(touch)

    def _current_x_view(self):
        if self._view_x is not None:
            return self._view_x
        xs_all = []
        for xs, _ys in self._series_data.values():
            xs_all.extend(xs)
        if not xs_all:
            return (0.0, 60.0)
        pad_x = max(5.0, (max(xs_all) - min(xs_all)) * 0.05)
        return (min(xs_all) - pad_x, max(xs_all) + pad_x)

    def _pan_pixels(self, dx):
        x_range = self._current_x_view()
        x_span = x_range[1] - x_range[0]
        if self.width <= 0:
            return
        self._view_x = (
            x_range[0] - dx * x_span / self.width,
            x_range[1] - dx * x_span / self.width,
        )
        self._schedule_render(force=True)

    def _zoom(self, scale, cx):
        x_range = self._current_x_view()
        rel_x = (cx - self.x) / float(self.width) if self.width else 0.5
        x0, x1 = x_range
        xc = x0 + (x1 - x0) * rel_x
        hx = (x1 - x0) * 0.5 / scale
        self._auto_x = False
        self._view_x = (xc - hx, xc + hx)
        self._schedule_render(force=True)
