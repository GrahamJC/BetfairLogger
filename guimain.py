import datetime as dt

from tkinter import *
from tkinter.ttk import *
from tkcalendar import DateEntry

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import numpy as np

import sqlalchemy as sql

from models import Event, Market

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'


class MainWindow:

    def __init__(self, master):
        self.master = master
        self.create_widgets()
        self.draw_graph()

    def date_selected(self, event = None):
        date = self.date_picker.get_date()
        markets = db_session.query(Market).filter(sql.cast(Market.start_time, sql.Date) == date).order_by(Market.start_time)
        self.market_combo['values'] = [f"{m.start_time:%H:%M}: {m.event.name}, {m.name}" for m in markets]
        self.market_combo.current(0)
        self.market_selected()

    def market_selected(self, event = None):
        print(self.market_combo.get())

    def create_widgets(self):
        Label(self.master, text = 'Select date: ').grid(row = 0, column = 0)
        self.date_picker = DateEntry(self.master)
        self.date_picker.grid(row = 0, column = 1)
        self.date_picker.bind('<<DateEntrySelected>>', self.date_selected)
        Label(self.master, text = 'Select event: ').grid(row = 0, column = 2)
        self.market_combo = Combobox(self.master, state = 'readonly')
        self.market_combo.grid(row = 0, column = 3, sticky = NSEW)
        self.market_combo.bind('<<ComboboxSelected>>', self.market_selected)
        #self.canvas = Canvas(self.master, width = 600, height = 400, background = 'lightblue')
        #self.canvas.grid(row = 1, column = 0, columnspan = 4, sticky = NSEW)
        self.master.columnconfigure(3, weight = 1)
        self.master.rowconfigure(1, weight = 1)

    def draw_graph(self):
        fig = Figure(figsize =  (5, 4), dpi = 100)
        t = np.arange(0, 3, 0.01)
        fig.add_subplot(111).plot(t, 2 * np.sin(2 * np.pi * t))
        canvas = FigureCanvasTkAgg(fig, master = self.master)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.grid(row = 1, column = 0, columnspan = 4, sticky = NSEW)


# Create DB engine and create session factory
db_engine = sql.create_engine(SQLALCHEMY_URL)
Session = sql.orm.sessionmaker(bind=db_engine)

# Create DB session
db_session = Session()

app = Tk()
main_window = MainWindow(app)
app.mainloop()

# Close DB session
db_session.close()
