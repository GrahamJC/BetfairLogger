import datetime as dt

from tkinter import *
from tkinter.ttk import *

import numpy as np
import pandas as pd
import sqlalchemy as sa
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from models import Event, Market, Runner, MarketRunner

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'
#SQLALCHEMY_URL = 'postgresql://postgres:barnum@localhost/betfairlogger'

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

    def __init__(self, master, db_session):
        self.master = master
        self.db_session = db_session
        self.option_period = IntVar()
        self.option_period.set(60)
        self.option_plot = StringVar()
        self.option_plot.set('MarketVolume')
        self.option_scale = StringVar()
        self.option_scale.set('Lin')
        self.option_update_auto = BooleanVar()
        self.option_update_auto.set(False)
        self.option_refresh = IntVar()
        self.option_refresh.set(0)
        self.create_widgets()
        self.year_combo.current(0)
        self.year_selected()
        #self.market_volume_data = None
        #self.market_data = None
        
    def year_selected(self, event = None):
        year = int(self.year_combo.get())
        months = [int(row[0]) for row in self.db_session.query(f"distinct date_part('month', start_time) from market where date_part('year', start_time) = {year} order by date_part('month', start_time)")]
        self.month_combo['values'] = months
        if months:
            self.month_combo.current(len(months) - 1)
            self.month_selected()

    def month_selected(self, event = None):
        year = int(self.year_combo.get())
        month = int(self.month_combo.get())
        days = [int(row[0]) for row in self.db_session.query(f"distinct date_part('day', start_time) from market where date_part('year', start_time) = {year} and date_part('month', start_time) = {month} order by date_part('day', start_time)")]
        self.day_combo['values'] = days
        if days:
            self.day_combo.current(len(days) - 1)
            self.day_selected()

    def day_selected(self, event = None):
        year = int(self.year_combo.get())
        month = int(self.month_combo.get())
        day = int(self.day_combo.get())
        date = dt.datetime(year, month, day)
        markets = self.db_session.query(Market).filter(sa.cast(Market.start_time, sa.Date) == date).order_by(Market.start_time)
        self.market_choices =  {f"{m.start_time:%H:%M}: {m.event.name}, {m.name}" : m.id for m in markets}
        self.market_combo['values'] = [k for k in self.market_choices.keys()]
        self.market_combo.current(0)
        self.market_selected()

    def market_selected(self, event = None):
        self.market_id = self.market_choices[self.market_combo.get()]
        self.update_volume_data(self.market_id)
        self.update_runners(self.market_id)
        self.update_market_data(self.market_id)
        self.draw_all_graphs(self.market_id)

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
        years = [int(row[0]) for row in self.db_session.query("distinct date_part('year', start_time) from market order by date_part('year', start_time) desc")]
        self.year_combo = Combobox(self.select_frame, state = 'readonly', width = 5, values = years)
        self.year_combo.pack(side = LEFT, padx = 5, pady = 5)
        self.year_combo.bind('<<ComboboxSelected>>', self.year_selected)
        Label(self.select_frame, text = 'Select event: ').pack(side = LEFT, padx = 5, pady = 5)
        self.market_combo = Combobox(self.select_frame, state = 'readonly')
        self.market_combo.pack(side = LEFT, fill = X, expand = True, padx = 5, pady = 5)
        self.market_combo.bind('<<ComboboxSelected>>', self.market_selected)
        self.select_frame.pack(side = TOP, fill = X, expand = False)

        # Options
        self.options_frame = Frame(self.master, width = 150)
        self.options_frame.pack(side = LEFT, fill = Y, expand = False)

        # Runners
        self.runner_frame = LabelFrame(self.options_frame, text = 'Runners')
        self.runner_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Label(self.runner_frame, text = 'Select event').pack(side = TOP)

        # Period
        self.period_frame = LabelFrame(self.options_frame, text = 'Period')
        self.period_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(self.period_frame, text = '60 mins', variable = self.option_period, value = 60, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = '30 mins', variable = self.option_period, value = 30, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = '10 mins', variable = self.option_period, value = 10, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = '5 mins', variable = self.option_period, value = 5, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(self.period_frame, text = 'Inplay', variable = self.option_period, value = 0, command = self.update_period).pack(side = TOP, anchor = W)

        # Plot variable
        self.plot_frame = LabelFrame(self.options_frame, text = 'Plot')
        self.plot_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(self.plot_frame, text = 'Market volume', variable = self.option_plot, value = 'MarketVolume', command = self.update_info_plot).pack(side = TOP, anchor = W)
        Radiobutton(self.plot_frame, text = 'Relative volume', variable = self.option_plot, value = 'RelativeVolume', command = self.update_info_plot).pack(side = TOP, anchor = W)
        Radiobutton(self.plot_frame, text = 'WOM', variable = self.option_plot, value = 'WOM', command = self.update_info_plot).pack(side = TOP, anchor = W)

        # Scale type
        self.scale_frame = LabelFrame(self.options_frame, text = 'Price scale')
        self.scale_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(self.scale_frame, text = 'Linear', variable = self.option_scale, value = 'Lin', command = self.update_price_plot).pack(side = TOP, anchor = W)
        Radiobutton(self.scale_frame, text = 'Logarithmic', variable = self.option_scale, value = 'Log', command = self.update_price_plot).pack(side = TOP, anchor = W)

        # Refresh
        self.refresh_frame = LabelFrame(self.options_frame, text = 'Refresh')
        self.refresh_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(self.refresh_frame, text = 'disable', variable = self.option_refresh, value = 0, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(self.refresh_frame, text = '1 second', variable = self.option_refresh, value = 1, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(self.refresh_frame, text = '5 seconds', variable = self.option_refresh, value = 5, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(self.refresh_frame, text = '15 seconds', variable = self.option_refresh, value = 15, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(self.refresh_frame, text = '30 seconds', variable = self.option_refresh, value = 30, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(self.refresh_frame, text = '60 seconds', variable = self.option_refresh, value = 60, command = self.auto_refresh).pack(side = TOP, anchor = W)

        # Plots
        self.plot_frame = Frame(self.master)
        self.plot_frame.pack(side = LEFT, fill = BOTH, expand = True)
        self.plot_frame.grid_rowconfigure(0, weight = 1)
        self.plot_frame.grid_rowconfigure(1, weight = 1)
        self.plot_frame.grid_rowconfigure(2, weight = 0)
        self.plot_frame.grid_columnconfigure(0, weight = 1)

        # Information plot
        self.info_plot_figure = matplotlib.figure.Figure(figsize = [10, 2])
        self.info_plot_ax = self.info_plot_figure.add_subplot()
        self.info_plot_canvas = FigureCanvasTkAgg(self.info_plot_figure, master = self.plot_frame)
        self.info_plot_widget = self.info_plot_canvas.get_tk_widget()
        self.info_plot_widget.grid(row = 0, column = 0, sticky = NSEW)
        self.info_plot_canvas.draw()

        # Price plot
        self.price_plot_figure = matplotlib.figure.Figure(figsize = [10, 8])
        self.price_plot_ax = self.price_plot_figure.add_subplot()
        self.price_plot_canvas = FigureCanvasTkAgg(self.price_plot_figure, master = self.plot_frame)
        self.price_plot_widget = self.price_plot_canvas.get_tk_widget()
        self.price_plot_widget.grid(row = 1, column = 0, sticky = NSEW)
        self.price_plot_canvas.draw()
        self.price_plot_toolbar_frame = Frame(self.plot_frame)
        self.price_plot_toolbar = NavigationToolbar2Tk(self.price_plot_canvas, self.price_plot_toolbar_frame)
        self.price_plot_toolbar.pack(side = TOP, fill = BOTH, expand = False)
        self.price_plot_toolbar_frame.grid(row = 2, column = 0)
        self.price_plot_toolbar.update()

    def update_runners(self, market_id):
        self.runners = [
            RunnerInfo(r.id, r.runner.name, r.starting_price)
            for r in self.db_session.query(MarketRunner).filter(MarketRunner.market_id == market_id) if r.starting_price
        ]
        self.runners.sort(key = lambda r: r.price)
        for i in range(min(3, len(self.runners))):
            self.runners[i].selected = True
        for widget in self.runner_frame.winfo_children():
            widget.destroy()
        for runner in self.runners:
            Checkbutton(self.runner_frame, text = f"{runner.name} ({runner.price})", variable = runner._selected, command = self.update_runners_selected).pack(side = TOP, anchor = 'w')

    def update_period(self):
        self.draw_all_graphs(self.market_id)

    def auto_refresh(self):
        secs = self.option_refresh.get()
        if secs:
            self.refresh_frame.after(secs * 1000, self.refresh)

    def refresh(self):
        self.update_volume_data(self.market_id)
        self.update_market_data(self.market_id)
        self.draw_all_graphs(self.market_id)
        secs = self.option_refresh.get()
        if secs:
            self.refresh_frame.after(secs * 1000, self.refresh)

    def update_info_plot(self):
        self.draw_info_graph(self.market_id)

    def update_price_plot(self):
        self.draw_price_graph(self.market_id)

    def update_runners_selected(self):
        self.update_info_plot()
        self.update_price_plot()

    def update_volume_data(self, market_id):
        query = (
            'select extract(epoch from mb.date_time - m.start_time)/60 mins, mb.inplay, mb.total_matched'
            ' from market_book mb'
            '   join market m on m.id = mb.market_id'
            f" where mb.market_id = {market_id}"
            ' and mb.status = \'OPEN\''
            ' order by mb.date_time'
        )
        data = pd.read_sql(query, db_engine, index_col = ['mins'])
        data['increase'] = data['total_matched'].diff()
        data['secs'] = data.index.to_series().diff() * 60
        data['rate'] = data['increase'] / data['secs']
        data['rate_smooth'] = data['rate'].rolling(window = 5).mean()
        self.market_volume_data = data

    def update_market_data(self, market_id):

        # Get market data
        query = (
            'select extract(epoch from mb.date_time - m.start_time)/60 mins, r.name, mb.inplay, mrb.last_price_traded, mrb.total_matched, (mrb.total_matched / mb.total_matched) * 100 percent, (mrb.wom_back / (mrb.wom_back + mrb.wom_lay)) * 100 wom'
            ' from market_book mb'
            '   join market m on m.id = mb.market_id'
            '   join market_runner_book mrb on mrb.market_book_id = mb.id'
            '   join market_runner mr on mr.id = mrb.market_runner_id'
            '   join runner r on r.id = mr.runner_id'
            f" where mb.market_id = {market_id}"
            ' and mb.status = \'OPEN\''
            ' order by mb.date_time, r.name'
        )
        data = pd.read_sql(query, db_engine, index_col = ['mins', 'name'])
        self.market_data = data

        # Get market orders
        query = (
            'select r.name, extract(epoch from mro.matched_date - m.start_time)/60 mins, side, price_matched, size'
            ' from market m'
            '   join market_runner_order mro on mro.market_id = m.id'
            '   join market_runner mr on mr.id = mro.market_runner_id'
            '   join runner r on r.id = mr.runner_id'
            f" where m.id = {market_id}"
            ' order by mro.placed_date'
        )
        data = pd.read_sql(query, db_engine, index_col = ['mins'])
        self.market_orders = data

    def draw_info_graph(self, market_id):
        self.info_plot_ax.clear()
        period = self.option_period.get()
        plot = self.option_plot.get()
        if plot == 'MarketVolume':
            data = self.market_volume_data
            if not data.empty:
                if period == 0:
                    data = data[data['inplay'] == True]
                else:
                    data = data[data['inplay'] == False]
                    data = data.query(f"mins >= -{period}")
                data[['rate', 'rate_smooth']].plot(ax = self.info_plot_ax)
        else:
            data = self.market_data
            if not data.empty:
                runners_selected = []
                for runner in self.runners:
                    if runner.selected:
                        runners_selected.append(runner.name)
                if runners_selected:
                    data = data.iloc[data.index.isin(runners_selected, level = 'name')]
                    if period == 0:
                        data = data[data['inplay'] == True]
                    else:
                        data = data[data['inplay'] == False]
                        data = data.query(f"mins >= -{period}")
                    if plot == 'RelativeVolume':
                        data['percent'].unstack().plot(ax = self.info_plot_ax)
                    elif plot == 'WOM':
                        data['wom'].unstack().plot(ax = self.info_plot_ax)
                self.info_plot_ax.legend(loc = 'upper left')
        self.info_plot_canvas.draw()

    def draw_price_graph(self, market_id):
        self.price_plot_ax.clear()
        data = self.market_data
        if not data.empty:
            runners_selected = []
            for runner in self.runners:
                if runner.selected:
                    runners_selected.append(runner.name)
            if runners_selected:
                data = data.iloc[data.index.isin(runners_selected, level = 'name')]
                period = self.option_period.get()
                plot = self.option_plot.get()
                scale = self.option_scale.get()
                if period == 0:
                    data = data[data['inplay'] == True]
                    data = data[data['last_price_traded'] <= 25]
                else:
                    data = data[data['inplay'] == False]
                    data = data.query(f"mins >= -{period}")
                data['last_price_traded'].unstack().plot(ax = self.price_plot_ax, logy = (scale == 'Log'))
                self.price_plot_ax.legend(loc = 'upper left')
                for index, row in self.market_orders.iterrows():
                    if row['name'] in runners_selected:
                        marker = 'v' if row['side'] == 'BACK' else '^'
                        self.price_plot_ax.plot([index], [row['price_matched']], marker, markersize = 12, markerfacecolor = 'white', markeredgecolor = 'black')
        self.price_plot_canvas.draw()

    def draw_all_graphs(self, market_id):
        self.draw_info_graph(market_id)
        self.draw_price_graph(market_id)


# Tell matplotlib to use the YkAgg backend
matplotlib.use('TkAgg')

# Create DB engine and create session factory
db_engine = sa.create_engine(SQLALCHEMY_URL)
Session = sa.orm.sessionmaker(bind=db_engine)

# Create DB session
db_session = Session()

root = Tk()
main_window = MainWindow(root, db_session)
root.mainloop()

# Close DB session
db_session.close()
