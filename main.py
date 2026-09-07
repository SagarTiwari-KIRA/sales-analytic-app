"""
Sales Analytics Dashboard - Kivy Edition
=========================================
A fully animated, touch-friendly rewrite of a console sales-analytics tool.
Single file, Kivy only (no matplotlib/pandas), so it packages cleanly with
Buildozer for Android.

Screens
-------
- Dashboard    : animated summary cards + a quick "sales by product" chart
- Add Sale     : a form to add new sales entries dynamically
- All Sales    : a scrollable, animated list of every sale (with delete)
- Charts       : switchable animated bar/line charts (product / region / month)

Run on desktop:
    python main.py

Package for Android:
    1. pip install buildozer cython
    2. buildozer init   (creates buildozer.spec)
    3. In buildozer.spec set: requirements = python3,kivy
    4. buildozer -v android debug
"""

import sqlite3
import os
from datetime import date

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse

if platform != "android":
    Window.size = (420, 780)
Window.clearcolor = (0.07, 0.09, 0.13, 1)

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BG = (0.07, 0.09, 0.13, 1)
CARD = (0.12, 0.14, 0.20, 1)
ACCENT = (0.30, 0.62, 0.98, 1)
ACCENT_DARK = (0.20, 0.45, 0.80, 1)
GOOD = (0.25, 0.78, 0.55, 1)
GOOD_DARK = (0.16, 0.58, 0.40, 1)
BAD = (0.90, 0.35, 0.38, 1)
BAD_DARK = (0.70, 0.22, 0.25, 1)
MUTED = (0.62, 0.66, 0.74, 1)
TEXT = (0.93, 0.95, 0.98, 1)
PALETTE = [
    (0.30, 0.62, 0.98, 1),
    (0.36, 0.82, 0.62, 1),
    (0.96, 0.70, 0.30, 1),
    (0.86, 0.42, 0.62, 1),
    (0.62, 0.52, 0.92, 1),
    (0.94, 0.50, 0.40, 1),
]


# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------
class Database:
    """Thin sqlite3 wrapper. No pandas so this stays Android-build friendly."""

    def __init__(self, path="sales_analytics.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_table()
        self._seed_if_empty()

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                product TEXT NOT NULL,
                category TEXT NOT NULL,
                region TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL
            )
        """)
        self.conn.commit()

    def _seed_if_empty(self):
        self.cursor.execute("SELECT COUNT(*) FROM sales")
        if self.cursor.fetchone()[0] == 0:
            sample = [
                ("2026-01-05", "Laptop", "Electronics", "North", 2, 60000),
                ("2026-01-10", "Phone", "Electronics", "South", 2, 30000),
                ("2026-01-15", "Chair", "Furniture", "East", 10, 4000),
                ("2026-01-15", "Table", "Furniture", "West", 5, 8000),
                ("2026-02-05", "Laptop", "Electronics", "North", 2, 60000),
                ("2026-02-10", "Phone", "Electronics", "South", 2, 25000),
                ("2026-02-15", "Chair", "Furniture", "East", 10, 4000),
                ("2026-02-15", "Table", "Furniture", "West", 5, 8000),
                ("2026-03-05", "Laptop", "Electronics", "North", 5, 60000),
                ("2026-03-10", "Phone", "Electronics", "South", 12, 23000),
                ("2026-03-15", "Chair", "Furniture", "East", 20, 5000),
                ("2026-03-15", "Table", "Furniture", "West", 15, 7000),
            ]
            self.cursor.executemany(
                """INSERT INTO sales
                   (sale_date, product, category, region, quantity, price)
                   VALUES (?,?,?,?,?,?)""",
                sample,
            )
            self.conn.commit()

    # -- writes ------------------------------------------------------------
    def add_sale(self, sale_date, product, category, region, quantity, price):
        self.cursor.execute(
            """INSERT INTO sales
               (sale_date, product, category, region, quantity, price)
               VALUES (?,?,?,?,?,?)""",
            (sale_date, product, category, region, quantity, price),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def delete_sale(self, sale_id):
        self.cursor.execute("DELETE FROM sales WHERE id=?", (sale_id,))
        self.conn.commit()

    # -- reads ---------------------------------------------------------
    def get_all_sales(self):
        self.cursor.execute("""
            SELECT id, sale_date, product, category, region, quantity, price,
                   quantity*price AS amount
            FROM sales
            ORDER BY sale_date DESC, id DESC
        """)
        return self.cursor.fetchall()

    def get_total_sales(self):
        self.cursor.execute("SELECT COALESCE(SUM(quantity*price),0) FROM sales")
        return self.cursor.fetchone()[0]

    def get_order_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM sales")
        return self.cursor.fetchone()[0]

    def get_distinct_product_count(self):
        self.cursor.execute("SELECT COUNT(DISTINCT product) FROM sales")
        return self.cursor.fetchone()[0]

    def get_sales_by_product(self):
        self.cursor.execute("""
            SELECT product, SUM(quantity), SUM(quantity*price) AS total
            FROM sales GROUP BY product ORDER BY total DESC
        """)
        return self.cursor.fetchall()

    def get_sales_by_region(self):
        self.cursor.execute("""
            SELECT region, SUM(quantity*price) AS total
            FROM sales GROUP BY region ORDER BY total DESC
        """)
        return self.cursor.fetchall()

    def get_monthly_sales(self):
        self.cursor.execute("""
            SELECT substr(sale_date,1,7) AS month, SUM(quantity*price) AS total
            FROM sales GROUP BY month ORDER BY month
        """)
        return self.cursor.fetchall()

    def get_top_product(self):
        self.cursor.execute("""
            SELECT product, SUM(quantity) AS qty
            FROM sales GROUP BY product ORDER BY qty DESC LIMIT 1
        """)
        return self.cursor.fetchone()

    def get_known_categories(self):
        self.cursor.execute("SELECT DISTINCT category FROM sales ORDER BY category")
        return [r[0] for r in self.cursor.fetchall()]

    def get_known_regions(self):
        self.cursor.execute("SELECT DISTINCT region FROM sales ORDER BY region")
        return [r[0] for r in self.cursor.fetchall()]


# ---------------------------------------------------------------------------
# Reusable animated widgets
# ---------------------------------------------------------------------------
class AnimatedButton(ButtonBehavior, Label):
    """A flat, rounded button with a press-flash animation."""

    bg_color = ListProperty(ACCENT)
    radius = NumericProperty(dp(14))

    def __init__(self, base_color=ACCENT, press_color=ACCENT_DARK, **kwargs):
        super().__init__(**kwargs)
        self.base_color = list(base_color)
        self.press_color = list(press_color)
        self.bg_color = list(base_color)
        self.bold = True
        self.color = TEXT
        self.markup = True
        with self.canvas.before:
            self._c = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size,
                                           radius=[self.radius])
        self.bind(pos=self._sync, size=self._sync, bg_color=self._recolor)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _recolor(self, *_):
        self._c.rgba = self.bg_color

    def set_palette(self, base_color, press_color):
        self.base_color = list(base_color)
        self.press_color = list(press_color)
        self.bg_color = list(base_color)

    def on_press(self):
        Animation.cancel_all(self, "bg_color")
        Animation(bg_color=self.press_color, duration=0.08).start(self)

    def on_release(self):
        Animation.cancel_all(self, "bg_color")
        Animation(bg_color=self.base_color, duration=0.18, t="out_quad").start(self)


class AnimatedNumber(Label):
    """A Label whose displayed number animates (counts up/down) on change."""

    value = NumericProperty(0)
    prefix = StringProperty("")
    decimals = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bold = True
        self.color = TEXT
        self.bind(value=self._render)
        self._render()

    def _render(self, *_):
        if self.decimals:
            self.text = f"{self.prefix}{self.value:,.{int(self.decimals)}f}"
        else:
            self.text = f"{self.prefix}{int(self.value):,}"

    def animate_to(self, target, duration=0.9):
        Animation.cancel_all(self, "value")
        Animation(value=target, duration=duration, t="out_cubic").start(self)


class BarChartWidget(Widget):
    """Simple animated vertical bar chart drawn on canvas."""

    def __init__(self, value_fmt=None, **kwargs):
        super().__init__(**kwargs)
        self.items = []          # list of (label, value)
        self.progress = 0.0
        self.value_fmt = value_fmt or (lambda v: f"{v:,.0f}")
        self._name_labels = []
        self._value_labels = []
        self.bind(pos=self._redraw, size=self._redraw)

    def set_items(self, items):
        self.items = items
        self.progress = 0.0
        self._rebuild_labels()
        self._redraw()
        anim = Animation(progress=1.0, duration=1.0, t="out_cubic")
        anim.bind(on_progress=lambda *a: self._redraw())
        anim.start(self)

    def on_progress(self, *_):
        pass

    def _rebuild_labels(self):
        for w in self._name_labels + self._value_labels:
            self.canvas.remove_group(str(id(w)))
        for w in self._name_labels + self._value_labels:
            if w.parent:
                w.parent.remove_widget(w)
        self._name_labels = []
        self._value_labels = []
        for label, value in self.items:
            nl = Label(text=str(label), font_size=dp(12), color=MUTED, size_hint=(None, None))
            vl = Label(text=self.value_fmt(value), font_size=dp(12), bold=True,
                       color=TEXT, size_hint=(None, None), opacity=0)
            self.add_widget(nl)
            self.add_widget(vl)
            self._name_labels.append(nl)
            self._value_labels.append(vl)

    def _redraw(self, *_):
        self.canvas.after.clear()
        if not self.items:
            return
        n = len(self.items)
        max_val = max(v for _, v in self.items) or 1
        pad_bottom = dp(28)
        pad_top = dp(20)
        gap = dp(14)
        chart_h = max(self.height - pad_bottom - pad_top, dp(10))
        chart_w = max(self.width - gap * (n + 1), dp(10))
        bar_w = chart_w / n

        with self.canvas.after:
            x = self.x + gap
            for idx, (label, value) in enumerate(self.items):
                h = (value / max_val) * chart_h * self.progress
                color = PALETTE[idx % len(PALETTE)]
                Color(*color)
                RoundedRectangle(pos=(x, self.y + pad_bottom), size=(bar_w, h),
                                  radius=[dp(6), dp(6), 0, 0])
                nl = self._name_labels[idx]
                vl = self._value_labels[idx]
                nl.size = (bar_w + dp(10), dp(18))
                nl.text_size = nl.size
                nl.halign = "center"
                nl.pos = (x - dp(5), self.y)
                vl.size = (bar_w + dp(20), dp(16))
                vl.text_size = vl.size
                vl.halign = "center"
                vl.pos = (x - dp(10), self.y + pad_bottom + h + dp(2))
                vl.opacity = 1 if self.progress > 0.85 else 0
                x += bar_w + gap


class LineChartWidget(Widget):
    """Animated monthly-trend line chart (points rise from baseline)."""

    def __init__(self, value_fmt=None, **kwargs):
        super().__init__(**kwargs)
        self.items = []
        self.progress = 0.0
        self.value_fmt = value_fmt or (lambda v: f"{v:,.0f}")
        self._name_labels = []
        self.bind(pos=self._redraw, size=self._redraw)

    def set_items(self, items):
        self.items = items
        self.progress = 0.0
        self._rebuild_labels()
        self._redraw()
        anim = Animation(progress=1.0, duration=1.1, t="out_cubic")
        anim.bind(on_progress=lambda *a: self._redraw())
        anim.start(self)

    def _rebuild_labels(self):
        for w in self._name_labels:
            if w.parent:
                w.parent.remove_widget(w)
        self._name_labels = []
        for label, _ in self.items:
            nl = Label(text=str(label), font_size=dp(11), color=MUTED, size_hint=(None, None))
            self.add_widget(nl)
            self._name_labels.append(nl)

    def _redraw(self, *_):
        self.canvas.after.clear()
        if not self.items:
            return
        n = len(self.items)
        max_val = max(v for _, v in self.items) or 1
        pad_bottom = dp(26)
        pad_top = dp(20)
        pad_side = dp(16)
        chart_h = max(self.height - pad_bottom - pad_top, dp(10))
        chart_w = max(self.width - pad_side * 2, dp(10))
        step = chart_w / max(n - 1, 1)

        points = []
        for idx, (label, value) in enumerate(self.items):
            x = self.x + pad_side + step * idx
            y = self.y + pad_bottom + (value / max_val) * chart_h * self.progress
            points.extend([x, y])
            nl = self._name_labels[idx]
            nl.size = (dp(50), dp(16))
            nl.text_size = nl.size
            nl.halign = "center"
            nl.pos = (x - dp(25), self.y)

        with self.canvas.after:
            Color(*ACCENT)
            if n > 1:
                Line(points=points, width=dp(2), joint="round", cap="round")
            for i in range(0, len(points), 2):
                Color(*ACCENT)
                r = dp(5)
                Ellipse(pos=(points[i] - r, points[i + 1] - r), size=(r * 2, r * 2))


# ---------------------------------------------------------------------------
# KV layout
# ---------------------------------------------------------------------------
KV = """
#:import dp kivy.metrics.dp

<NavBar@BoxLayout>:
    size_hint_y: None
    height: dp(56)
    padding: dp(8), dp(6)
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: 0.10, 0.12, 0.17, 1
        Rectangle:
            pos: self.pos
            size: self.size

<SectionLabel@Label>:
    bold: True
    font_size: dp(20)
    color: 0.93, 0.95, 0.98, 1
    size_hint_y: None
    height: dp(36)
    halign: "left"
    valign: "middle"
    text_size: self.size

<FieldLabel@Label>:
    color: 0.62, 0.66, 0.74, 1
    font_size: dp(13)
    size_hint_y: None
    height: dp(20)
    halign: "left"
    text_size: self.size

<StyledInput@TextInput>:
    size_hint_y: None
    height: dp(44)
    multiline: False
    padding: dp(10), dp(12)
    background_color: 0.16, 0.19, 0.26, 1
    foreground_color: 0.93, 0.95, 0.98, 1
    cursor_color: 0.30, 0.62, 0.98, 1
    hint_text_color: 0.5, 0.53, 0.6, 1

<Card@BoxLayout>:
    orientation: "vertical"
    padding: dp(12)
    spacing: dp(4)
    canvas.before:
        Color:
            rgba: 0.12, 0.14, 0.20, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<DashboardScreen>:
    BoxLayout:
        orientation: "vertical"
        NavBar:
            AnimatedButton:
                text: "Dashboard"
                on_release: app.switch_screen("dashboard")
            AnimatedButton:
                text: "Add Sale"
                on_release: app.switch_screen("add_sale")
            AnimatedButton:
                text: "All Sales"
                on_release: app.switch_screen("all_sales")
            AnimatedButton:
                text: "Charts"
                on_release: app.switch_screen("charts")
        ScrollView:
            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(16)
                spacing: dp(14)

                SectionLabel:
                    text: "Sales Analytics"

                Card:
                    size_hint_y: None
                    height: dp(90)
                    FieldLabel:
                        text: "TOTAL SALES"
                    AnimatedNumber:
                        id: total_sales_num
                        prefix: "\\u20B9"
                        font_size: dp(30)

                BoxLayout:
                    size_hint_y: None
                    height: dp(84)
                    spacing: dp(12)
                    Card:
                        FieldLabel:
                            text: "ORDERS"
                        AnimatedNumber:
                            id: total_orders_num
                            font_size: dp(24)
                    Card:
                        FieldLabel:
                            text: "PRODUCTS"
                        AnimatedNumber:
                            id: total_products_num
                            font_size: dp(24)

                Card:
                    size_hint_y: None
                    height: dp(80)
                    FieldLabel:
                        text: "TOP SELLER"
                    Label:
                        id: top_product_label
                        text: "--"
                        bold: True
                        font_size: dp(20)
                        color: 0.93, 0.95, 0.98, 1
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: dp(28)

                SectionLabel:
                    text: "Sales by Product"

                Card:
                    size_hint_y: None
                    height: dp(230)
                    BoxLayout:
                        id: dash_chart_holder

<AddSaleScreen>:
    BoxLayout:
        orientation: "vertical"
        NavBar:
            AnimatedButton:
                text: "Dashboard"
                on_release: app.switch_screen("dashboard")
            AnimatedButton:
                text: "Add Sale"
                on_release: app.switch_screen("add_sale")
            AnimatedButton:
                text: "All Sales"
                on_release: app.switch_screen("all_sales")
            AnimatedButton:
                text: "Charts"
                on_release: app.switch_screen("charts")
        ScrollView:
            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(16)
                spacing: dp(10)

                SectionLabel:
                    text: "Add a New Sale"

                FieldLabel:
                    text: "Product name"
                StyledInput:
                    id: in_product
                    hint_text: "e.g. Monitor"

                FieldLabel:
                    text: "Category"
                StyledInput:
                    id: in_category
                    hint_text: "e.g. Electronics"

                FieldLabel:
                    text: "Region"
                StyledInput:
                    id: in_region
                    hint_text: "e.g. North"

                FieldLabel:
                    text: "Quantity"
                StyledInput:
                    id: in_quantity
                    hint_text: "e.g. 3"
                    input_filter: "int"

                FieldLabel:
                    text: "Price per unit"
                StyledInput:
                    id: in_price
                    hint_text: "e.g. 1999.00"
                    input_filter: "float"

                FieldLabel:
                    text: "Date (YYYY-MM-DD)"
                StyledInput:
                    id: in_date
                    hint_text: "YYYY-MM-DD"

                Widget:
                    size_hint_y: None
                    height: dp(6)

                Label:
                    id: form_message
                    text: ""
                    color: 0.25, 0.78, 0.55, 1
                    bold: True
                    size_hint_y: None
                    height: dp(24)
                    opacity: 0

                AnimatedButton:
                    id: submit_btn
                    text: "Add Sale"
                    size_hint_y: None
                    height: dp(50)
                    on_release: app.submit_sale()

<AllSalesScreen>:
    BoxLayout:
        orientation: "vertical"
        NavBar:
            AnimatedButton:
                text: "Dashboard"
                on_release: app.switch_screen("dashboard")
            AnimatedButton:
                text: "Add Sale"
                on_release: app.switch_screen("add_sale")
            AnimatedButton:
                text: "All Sales"
                on_release: app.switch_screen("all_sales")
            AnimatedButton:
                text: "Charts"
                on_release: app.switch_screen("charts")
        BoxLayout:
            orientation: "vertical"
            padding: dp(16), dp(12)
            spacing: dp(8)
            SectionLabel:
                text: "All Sales"
            ScrollView:
                GridLayout:
                    id: sales_list
                    cols: 1
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)

<ChartsScreen>:
    BoxLayout:
        orientation: "vertical"
        NavBar:
            AnimatedButton:
                text: "Dashboard"
                on_release: app.switch_screen("dashboard")
            AnimatedButton:
                text: "Add Sale"
                on_release: app.switch_screen("add_sale")
            AnimatedButton:
                text: "All Sales"
                on_release: app.switch_screen("all_sales")
            AnimatedButton:
                text: "Charts"
                on_release: app.switch_screen("charts")
        BoxLayout:
            orientation: "vertical"
            padding: dp(16), dp(12)
            spacing: dp(10)
            SectionLabel:
                text: "Charts"
            BoxLayout:
                size_hint_y: None
                height: dp(46)
                spacing: dp(8)
                AnimatedButton:
                    id: btn_chart_product
                    text: "By Product"
                    on_release: app.show_chart("product")
                AnimatedButton:
                    id: btn_chart_region
                    text: "By Region"
                    on_release: app.show_chart("region")
                AnimatedButton:
                    id: btn_chart_month
                    text: "Monthly"
                    on_release: app.show_chart("month")
            Card:
                BoxLayout:
                    id: chart_holder
"""


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------
class DashboardScreen(Screen):
    def on_pre_enter(self, *_):
        App.get_running_app().refresh_dashboard()


class AddSaleScreen(Screen):
    def on_pre_enter(self, *_):
        if not self.ids.in_date.text:
            self.ids.in_date.text = date.today().isoformat()


class AllSalesScreen(Screen):
    def on_pre_enter(self, *_):
        App.get_running_app().refresh_sales_list()


class ChartsScreen(Screen):
    def on_pre_enter(self, *_):
        App.get_running_app().show_chart(
            getattr(App.get_running_app(), "current_chart", "product")
        )


# ---------------------------------------------------------------------------
# Sale row widget for "All Sales" screen
# ---------------------------------------------------------------------------
class SaleRow(BoxLayout):
    def __init__(self, sale, on_delete, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(58),
                          padding=(dp(10), dp(6)), spacing=dp(8), **kwargs)
        self.opacity = 0
        self.sale_id = sale[0]
        with self.canvas.before:
            self._c = Color(0.12, 0.14, 0.20, 1)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._sync, size=self._sync)

        info = BoxLayout(orientation="vertical")
        title = Label(text=f"[b]{sale[2]}[/b]  \u00b7  {sale[3]}", markup=True,
                      font_size=dp(14), color=TEXT, halign="left", valign="top")
        sub = Label(text=f"{sale[1]}  \u00b7  {sale[4]}  \u00b7  qty {sale[5]}",
                    font_size=dp(11), color=MUTED, halign="left", valign="bottom")
        for lbl in (title, sub):
            lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        info.add_widget(title)
        info.add_widget(sub)

        amount = Label(text=f"\u20B9{sale[7]:,.0f}", bold=True, color=GOOD,
                        size_hint_x=None, width=dp(90), font_size=dp(14))

        del_btn = AnimatedButton(text="\u00d7", base_color=BAD, press_color=BAD_DARK,
                                  size_hint=(None, None), size=(dp(34), dp(34)),
                                  font_size=dp(18))
        del_btn.bind(on_release=lambda *_: on_delete(self))

        self.add_widget(info)
        self.add_widget(amount)
        self.add_widget(del_btn)

        Animation(opacity=1, duration=0.28, t="out_quad").start(self)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class SalesAnalyticsApp(App):
    def build(self):
        self.title = "Sales Analytics"
        self.db = Database()
        self.current_chart = "product"
        self._screen_order = ["dashboard", "add_sale", "all_sales", "charts"]
        root = Builder.load_string(KV)
        self.sm = ScreenManager(transition=SlideTransition(duration=0.22))
        self.sm.add_widget(DashboardScreen(name="dashboard"))
        self.sm.add_widget(AddSaleScreen(name="add_sale"))
        self.sm.add_widget(AllSalesScreen(name="all_sales"))
        self.sm.add_widget(ChartsScreen(name="charts"))
        return self.sm

    # -- navigation ----------------------------------------------------
    def switch_screen(self, name):
        if name == self.sm.current:
            return
        cur_i = self._screen_order.index(self.sm.current)
        new_i = self._screen_order.index(name)
        self.sm.transition.direction = "left" if new_i > cur_i else "right"
        self.sm.current = name

    # -- dashboard -------------------------------------------------------
    def refresh_dashboard(self):
        scr = self.sm.get_screen("dashboard")
        total = self.db.get_total_sales()
        orders = self.db.get_order_count()
        products = self.db.get_distinct_product_count()
        top = self.db.get_top_product()

        scr.ids.total_sales_num.animate_to(total)
        scr.ids.total_orders_num.animate_to(orders)
        scr.ids.total_products_num.animate_to(products)
        if top:
            scr.ids.top_product_label.text = f"\U0001F3C6 {top[0]}  ({top[1]} units)"
        else:
            scr.ids.top_product_label.text = "--"

        holder = scr.ids.dash_chart_holder
        holder.clear_widgets()
        chart = BarChartWidget(value_fmt=lambda v: f"{v/1000:,.0f}k")
        holder.add_widget(chart)
        data = [(p, t) for p, q, t in self.db.get_sales_by_product()]
        Clock.schedule_once(lambda dt: chart.set_items(data), 0.05)

    # -- add sale --------------------------------------------------------
    def submit_sale(self):
        scr = self.sm.get_screen("add_sale")
        ids = scr.ids
        product = ids.in_product.text.strip()
        category = ids.in_category.text.strip()
        region = ids.in_region.text.strip()
        qty_text = ids.in_quantity.text.strip()
        price_text = ids.in_price.text.strip()
        sale_date = ids.in_date.text.strip() or date.today().isoformat()

        errors = []
        if not product:
            errors.append(ids.in_product)
        if not category:
            errors.append(ids.in_category)
        if not region:
            errors.append(ids.in_region)
        try:
            quantity = int(qty_text)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            errors.append(ids.in_quantity)
            quantity = None
        try:
            price = float(price_text)
            if price <= 0:
                raise ValueError
        except ValueError:
            errors.append(ids.in_price)
            price = None

        if errors:
            for field in errors:
                self._shake(field)
            self._flash_message(ids.form_message, "Please check the highlighted fields",
                                 BAD)
            return

        self.db.add_sale(sale_date, product, category, region, quantity, price)

        # clear form (keep date so multiple same-day entries are quick)
        ids.in_product.text = ""
        ids.in_category.text = ""
        ids.in_region.text = ""
        ids.in_quantity.text = ""
        ids.in_price.text = ""

        self._flash_message(ids.form_message, f"Added {product} \u2713", GOOD)

    def _flash_message(self, label, text, color):
        label.text = text
        label.color = color
        label.opacity = 0
        anim = Animation(opacity=1, duration=0.2) + Animation(opacity=1, duration=1.0) \
            + Animation(opacity=0, duration=0.5)
        anim.start(label)

    def _shake(self, widget):
        orig_x = widget.x
        anim = (
            Animation(x=orig_x - dp(6), duration=0.04)
            + Animation(x=orig_x + dp(6), duration=0.04)
            + Animation(x=orig_x - dp(4), duration=0.04)
            + Animation(x=orig_x, duration=0.04)
        )
        anim.start(widget)

    # -- all sales ---------------------------------------------------------
    def refresh_sales_list(self):
        scr = self.sm.get_screen("all_sales")
        grid = scr.ids.sales_list
        grid.clear_widgets()
        rows = self.db.get_all_sales()
        for i, sale in enumerate(rows):
            row = SaleRow(sale, on_delete=self._delete_row)
            row.opacity = 0
            grid.add_widget(row)
            Clock.schedule_once(
                lambda dt, r=row: Animation(opacity=1, duration=0.25).start(r),
                0.02 * i,
            )

    def _delete_row(self, row):
        anim = Animation(opacity=0, height=0, duration=0.22, t="in_quad")

        def finish(*_):
            self.db.delete_sale(row.sale_id)
            if row.parent:
                row.parent.remove_widget(row)

        anim.bind(on_complete=finish)
        anim.start(row)

    # -- charts --------------------------------------------------------
    def show_chart(self, kind):
        self.current_chart = kind
        scr = self.sm.get_screen("charts")
        holder = scr.ids.chart_holder
        holder.clear_widgets()

        palette_map = {
            "product": ("btn_chart_product", scr.ids.btn_chart_product),
            "region": ("btn_chart_region", scr.ids.btn_chart_region),
            "month": ("btn_chart_month", scr.ids.btn_chart_month),
        }
        for key, (_, btn) in palette_map.items():
            if key == kind:
                btn.set_palette(ACCENT, ACCENT_DARK)
            else:
                btn.set_palette((0.16, 0.19, 0.26, 1), (0.12, 0.14, 0.20, 1))

        if kind == "product":
            chart = BarChartWidget(value_fmt=lambda v: f"{v/1000:,.0f}k")
            data = [(p, t) for p, q, t in self.db.get_sales_by_product()]
        elif kind == "region":
            chart = BarChartWidget(value_fmt=lambda v: f"{v/1000:,.0f}k")
            data = self.db.get_sales_by_region()
        else:
            chart = LineChartWidget(value_fmt=lambda v: f"{v/1000:,.0f}k")
            data = self.db.get_monthly_sales()

        holder.add_widget(chart)
        Clock.schedule_once(lambda dt: chart.set_items(data), 0.05)


if __name__ == "__main__":
    SalesAnalyticsApp().run()
