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

from models import Event, Market, Runner, MarketRunner

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'

class RunnerInfo:

    def __init__(self, id, name, price, selected = False):
        self.id = id
        self.name = name
        self.price = price
        self._selected = BooleanVar()
        self._selected.set(selected)

    def _get_selected(self):
        return self._selected.get()

    def _set_selected(self, value):
        self._selected.set(value)

    selected = property(_get_selected, _set_selected)


class MainWindow:

    def __init__(self, master):
        self.master = master
        self.option_period = IntVar()
        self.option_period.set(60)
        self.option_plot = StringVar()
        self.option_plot.set('Price')
        self.create_widgets()
        self.year_combo.current(0)
        self.year_selected()

    def year_selected(self, event = None):
        year = int(self.year_combo.get())
        months = [int(row[0]) for row in db_session.query(f"distinct date_part('month', start_time) from market where date_part('year', start_time) = {year} order by date_part('month', start_time)")]
        self.month_combo['values'] = months
        if months:
            self.month_combo.current(len(months) - 1)
            self.month_selected()

    def month_selected(self, event = None):
        year = int(self.year_combo.get())
        month = int(self.month_combo.get())
        days = [int(row[0]) for row in db_session.query(f"distinct date_part('day', start_time) from market where date_part('year', start_time) = {year} and date_part('month', start_time) = {month} order by date_part('day', start_time)")]
        self.day_combo['values'] = days
        if days:
            self.day_combo.current(len(days) - 1)
            self.day_selected()

    def day_selected(self, event = None):
        year = int(self.year_combo.get())
        month = int(self.month_combo.get())
        day = int(self.day_combo.get())
        date = dt.datetime(year, month, day)
        markets = db_session.query(Market).filter(sa.cast(Market.start_time, sa.Date) == date).order_by(Market.start_time)
        self.market_choices =  {f"{m.start_time:%H:%M}: {m.event.name}, {m.name}" : m.id for m in markets}
        self.market_combo['values'] = [k for k in self.market_choices.keys()]
        self.market_combo.current(0)
        self.market_selected()

    def market_selected(self, event = None):
        self.market_id = self.market_choices[self.market_combo.get()]
        self.update_runners(self.market_id)
        self.update_market_data(self.market_id)
        self.draw_graph(self.market_id)

    def create_widgets(self):

        self.select_frame = Frame(self.master)
        Label(self.select_frame, text = 'Day: ').pack(side = LEFT, padx = 5, pady = 5)
        self.day_combo = Combobox(self.select_frame, state = 'readonly', width = 5)
        self.day_combo.pack(side = LEFT, padx = 5, pady = 5)
        self.day_combo.bind('<<ComboboxSelected>>', self.day_selected)
        Label(self.select_frame, text = 'Month: ').pack(side = LEFT, padx = 5, pady = 5)
        self.month_combo = Combobox(self.select_frame, state = 'readonly', width = 5)
        self.month_combo.pack(side = LEFT, padx = 5, pady = 5)
        self.month_combo.bind('<<ComboboxSelected>>', self.month_selected)
        Label(self.select_frame, text = 'Year: ').pack(side = LEFT, padx = 5, pady = 5)
        years = [int(row[0]) for row in db_session.query("distinct date_part('year', start_time) from market order by date_part('year', start_time) desc")]
        self.year_combo = Combobox(self.select_frame, state = 'readonly', width = 5, values = years)
        self.year_combo.pack(side = LEFT, padx = 5, pady = 5)
        self.year_combo.bind('<<ComboboxSelected>>', self.year_selected)
        Label(self.select_frame, text = 'Select event: ').pack(side = LEFT, padx = 5, pady = 5)
        self.market_combo = Combobox(self.select_frame, state = 'readonly')
        self.market_combo.pack(side = LEFT, fill = X, expand = True, padx = 5, pady = 5)
        self.market_combo.bind('<<ComboboxSelected>>', self.market_selected)
        self.select_frame.pack(side = TOP, fill = X, expand = False)

        self.options_frame = Frame(self.master, width = 150)
        self.runner_frame = LabelFrame(self.options_frame, text = 'Runners')
        Label(self.runner_frame, text = 'Select event').pack(side = TOP)
        self.runner_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        self.period_frame = LabelFrame(self.options_frame, text = 'Period')
        Radiobutton(self.period_frame, text = '60 mins', variable = self.option_period, value = 60, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = '30 mins', variable = self.option_period, value = 30, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = '10 mins', variable = self.option_period, value = 10, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = '5 mins', variable = self.option_period, value = 5, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = 'Inplay', variable = self.option_period, value = 0, command = self.update_period).pack(side = TOP, anchor = W)
        self.period_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        self.plot_frame = LabelFrame(self.options_frame, text = 'Plot')
        Radiobutton(self.plot_frame, text = 'Price', variable = self.option_plot, value = 'Price', command = self.update_plot).pack(side = TOP, anchor = W)
        Radiobutton(self.plot_frame, text = 'Volume', variable = self.option_plot, value = 'Volume', command = self.update_plot).pack(side = TOP, anchor = W)
        Radiobutton(self.plot_frame, text = 'Volume (percent)', variable = self.option_plot, value = 'VolumePercent', command = self.update_plot).pack(side = TOP, anchor = W)
        self.plot_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        self.options_frame.pack(side = LEFT, fill = Y, expand = False)

        self.graph_frame = Frame(self.master)
        self.graph_frame.pack(side = LEFT, fill = BOTH, expand = True)
        self.graph_figure = matplotlib.figure.Figure()
        self.graph_ax = self.graph_figure.add_subplot()
        self.graph_canvas = FigureCanvasTkAgg(self.graph_figure, master = self.graph_frame)
        self.graph_widget = self.graph_canvas.get_tk_widget()
        self.graph_widget.pack(side = TOP, fill = BOTH, expand = 1)
        self.graph_canvas.draw()
        self.graph_toolbar = NavigationToolbar2Tk(self.graph_canvas, self.graph_frame)
        self.graph_toolbar.pack(side = TOP, fill = BOTH, expand = 0)
        self.graph_toolbar.update()

        self.master.columnconfigure(3, weight = 1)
        self.master.rowconfigure(1, weight = 1)

    def update_runners(self, market_id):
        self.runners = [
            RunnerInfo(r.id, r.runner.name, r.starting_price)
            for r in db_session.query(MarketRunner).filter(MarketRunner.market_id == market_id) if r.starting_price
        ]
        self.runners.sort(key = lambda r: r.price)
        for i in range(min(3, len(self.runners))):
            self.runners[i].selected = True
        for widget in self.runner_frame.winfo_children():
            widget.destroy()
        for runner in self.runners:
            Checkbutton(self.runner_frame, text = f"{runner.name} ({runner.price})", variable = runner._selected, command = self.update_runners_selected).pack(side = TOP, anchor = 'w')

    def update_period(self):
        self.draw_graph(self.market_id)

    def update_plot(self):
        self.draw_graph(self.market_id)

    def update_runners_selected(self):
        self.draw_graph(self.market_id)

    def update_market_data(self, market_id):
        query = (
            'select extract(epoch from mb.date_time - m.start_time)/60 mins, r.name, mb.inplay, mrb.last_price_traded, mrb.total_matched, (mrb.total_matched / mb.total_matched) * 100 percent'
            ' from market_book mb'
            '   join market m on m.id = mb.market_id'
            '   join market_runner_book mrb on mrb.market_book_id = mb.id'
            '   join market_runner mr on mr.id = mrb.market_runner_id'
            '   join runner r on r.id = mr.runner_id'
            f" where mb.market_id = {market_id}"
            ' and mb.status = \'OPEN\''
            ' order by mb.date_time, r.name'
        )
        self.market_data = pd.read_sql(query, db_engine, index_col = ['mins', 'name'])

    def draw_graph(self, market_id):
        self.graph_ax.clear()
        runners_selected = []
        for runner in self.runners:
             if runner.selected:
                 runners_selected.append(runner.name)
        if runners_selected:
            data = self.market_data
            data = data.iloc[data.index.isin(runners_selected, level = 1)]
            period = self.option_period.get()
            plot = self.option_plot.get()
            if period == 0:
                data = data[data['inplay'] == True]
                if plot == 'Price':
                    data = data[data['last_price_traded'] <= 25]
            else:
                data = data[data['inplay'] == False]
                data = data.query(f"mins >= -{period}")
            if plot == 'Price':
                data['last_price_traded'].unstack().plot(ax = self.graph_ax)
            elif plot == 'Volume':
                data['total_matched'].unstack().plot(ax = self.graph_ax)
            elif plot == 'VolumePercent':
                data['percent'].unstack().plot(ax = self.graph_ax)
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
