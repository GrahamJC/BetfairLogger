import datetime as dt

from tkinter import *
from tkinter.ttk import *
from tkcalendar import DateEntry

import numpy as np
import pandas as pd
import sqlalchemy as sa
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from models import Event, Market, Runner

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'


class MainWindow:

    def __init__(self, master):
        self.master = master
        self.create_widgets()

    def date_selected(self, event = None):
        date = self.date_picker.get_date()
        markets = db_session.query(Market).filter(sa.cast(Market.start_time, sa.Date) == date).order_by(Market.start_time)
        self.market_choices =  {f"{m.start_time:%H:%M}: {m.event.name}, {m.name}" : m.id for m in markets}
        self.market_combo['values'] = [k for k in self.market_choices.keys()]
        self.market_combo.current(0)
        self.market_selected()

    def market_selected(self, event = None):
        self.market_id = self.market_choices[self.market_combo.get()]
        self.update_runners(self.market_id)
        self.draw_graph(self.market_id)

    def create_widgets(self):
        Label(self.master, text = 'Select date: ').grid(row = 0, column = 0)
        self.date_picker = DateEntry(self.master)
        self.date_picker.grid(row = 0, column = 1)
        self.date_picker.bind('<<DateEntrySelected>>', self.date_selected)
        Label(self.master, text = 'Select event: ').grid(row = 0, column = 2)
        self.market_combo = Combobox(self.master, state = 'readonly')
        self.market_combo.grid(row = 0, column = 3, sticky = NSEW)
        self.market_combo.bind('<<ComboboxSelected>>', self.market_selected)
        self.runner_frame = Frame(self.master)

        self.graph_figure = matplotlib.figure.Figure()
        self.graph_ax = self.graph_figure.add_subplot()
        self.graph_frame = Frame(self.master)
        self.graph_canvas = FigureCanvasTkAgg(self.graph_figure, master = self.graph_frame)
        self.graph_widget = self.graph_canvas.get_tk_widget()
        self.graph_widget.pack(side = TOP, fill = BOTH, expand = 1)
        self.graph_canvas.draw()
        self.graph_toolbar = NavigationToolbar2Tk(self.graph_canvas, self.graph_frame)
        self.graph_toolbar.pack(side = TOP, fill = BOTH, expand = 0)
        self.graph_toolbar.update()
        self.graph_frame.grid(row = 1, column = 2, columnspan = 3, sticky = NSEW)

        self.master.columnconfigure(3, weight = 1)
        self.master.rowconfigure(1, weight = 1)

    def update_runners(self, market_id):
        self.runners = {r.name:BooleanVar(False) for r in db_session.query(Runner).filter(Runner.market_id == market_id).order_by(Runner.name)}
        self.runner_frame.grid_forget()
        self.runner_frame.destroy()
        self.runner_frame = Frame(self.master)
        for name, var in self.runners.items():
            Checkbutton(self.runner_frame, text = name, variable = var, command = self.update_runners_selected).pack(side = TOP, anchor = 'w')
        self.runner_frame.grid(row = 1, column = 0, columnspan = 2, sticky = NSEW)

    def update_runners_selected(self):
        print('Runners selected:')
        for runner, selected in self.runners.items():
            if selected.get():
                print(f"  {runner}")

    def draw_graph(self, market_id):
        query = (
            'select mb.date_time, r.name, rb.last_price_traded, rb.total_matched'
            ' from market_book mb'
            '   join runner_book rb on rb.market_book_id = mb.id'
            '   join runner r on r.id = rb.runner_id'
            f' where mb.market_id = {market_id}'
            ' and mb.status = \'OPEN\''
            ' and not mb.inplay'
            ' order by mb.date_time, r.name'
        )
        data = pd.read_sql(query, db_engine, index_col = ['date_time', 'name'])
        self.graph_ax.clear()
        data['last_price_traded'].unstack().plot(ax = self.graph_ax)
        self.graph_canvas.draw()


# Tell matplotlib to use the YkAgg backend
matplotlib.use('TkAgg')

# Create DB engine and create session factory
db_engine = sa.create_engine(SQLALCHEMY_URL)
Session = sa.orm.sessionmaker(bind=db_engine)

# Create DB session
db_session = Session()

root = Tk()
main_window = MainWindow(root)
root.mainloop()

# Close DB session
db_session.close()
