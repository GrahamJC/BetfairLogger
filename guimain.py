import datetime as dt
import time as tm
import pytz

from tkinter import *
from tkinter.ttk import *

import numpy as np
import pandas as pd
import sqlalchemy as sa
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from models import Event, Market, Runner, MarketRunner

# DB connection URL
SQLALCHEMY_URL = 'postgresql://postgres:barnum@qnap:32768/betfairlogger'
#SQLALCHEMY_URL = 'postgresql://postgres:barnum@localhost/betfairlogger'
#SQLALCHEMY_URL = 'postgresql://graham@gc-postgresql:CK6Z9wC3x@gc-postgresql.postgres.database.azure.com/betfairlogger'

class RunnerInfo:

    def __init__(self, id, name, sort_priority, starting_price, selected = False):
        self.id = id
        self.name = name
        self.sort_priority = sort_priority
        self.starting_price = starting_price
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
        self.timezone = pytz.timezone('Europe/London')
        self.info_total = StringVar()
        self.info_prerace = StringVar()
        self.info_inplay = StringVar()
        self.info_profit = StringVar()
        self.option_period = IntVar()
        self.option_period.set(240)
        self.option_plot = StringVar()
        self.option_plot.set('Relative')
        self.option_price = StringVar()
        self.option_price.set('Spread')
        self.option_price_smoothed = BooleanVar()
        self.option_price_smoothed.set(False)
        self.option_scale = StringVar()
        self.option_scale.set('Log')
        self.option_update_auto = BooleanVar()
        self.option_update_auto.set(False)
        self.option_refresh = IntVar()

        self.option_refresh.set(0)
        self.create_widgets()
        self.year_combo.current(0)
        self.year_selected()
        self.refresh_id = None
        
    def refresh_markets(self):
        year = int(self.year_combo.get())
        month = int(self.month_combo.get())
        day = int(self.day_combo.get())
        date = dt.datetime(year, month, day)
        markets = self.db_session.query(Market).filter(sa.cast(Market.start_time, sa.Date) == date).order_by(Market.start_time)
        self.market_choices =  {f"{self.timezone.fromutc(m.start_time):%H:%M}: {m.event.name}, {m.name} (£{round(m.profit, 2)})" : m.id for m in markets}
        self.market_combo['values'] = [k for k in self.market_choices.keys()]
        self.market_combo.current(0)
        self.market_selected()
        
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
        self.refresh_markets()

    def market_selected(self, event = None):
        self.market_id = self.market_choices[self.market_combo.get()]
        #start_time = tm.time()
        self.update_notes(self.market_id)
        #print(f"update_notes: {tm.time() - start_time}")
        #start_time = tm.time()
        self.update_runners(self.market_id)
        #print(f"update_runners: {tm.time() - start_time}")
        #start_time = tm.time()
        self.update_volume_data(self.market_id)
        #print(f"update_volume_data: {tm.time() - start_time}")
        #start_time = tm.time()
        self.update_market_data(self.market_id)
        #print(f"update_market_data: {tm.time() - start_time}")
        #start_time = tm.time()
        self.update_info(self.market_id)
        #print(f"update_info: {tm.time() - start_time}")
        #start_time = tm.time()
        self.draw_all_graphs(self.market_id)
        #print(f"draw_all_graphs: {tm.time() - start_time}")

    def create_widgets(self):

        # Date and market selection
        frame = Frame(self.master)
        Label(frame, text = 'Year: ').pack(side = LEFT, padx = 5, pady = 5)
        years = [int(row[0]) for row in self.db_session.query("distinct date_part('year', start_time) from market order by date_part('year', start_time) desc")]
        self.year_combo = Combobox(frame, state = 'readonly', width = 5, values = years)
        self.year_combo.pack(side = LEFT, padx = 5, pady = 5)
        self.year_combo.bind('<<ComboboxSelected>>', self.year_selected)
        Label(frame, text = 'Month: ').pack(side = LEFT, padx = 5, pady = 5)
        self.month_combo = Combobox(frame, state = 'readonly', width = 5)
        self.month_combo.pack(side = LEFT, padx = 5, pady = 5)
        self.month_combo.bind('<<ComboboxSelected>>', self.month_selected)
        Label(frame, text = 'Day: ').pack(side = LEFT, padx = 5, pady = 5)
        self.day_combo = Combobox(frame, state = 'readonly', width = 5)
        self.day_combo.pack(side = LEFT, padx = 5, pady = 5)
        self.day_combo.bind('<<ComboboxSelected>>', self.day_selected)
        Label(frame, text = 'Select event: ').pack(side = LEFT, padx = 5, pady = 5)
        self.market_combo = Combobox(frame, state = 'readonly')
        self.market_combo.pack(side = LEFT, fill = X, expand = True, padx = 5, pady = 5)
        self.market_combo.bind('<<ComboboxSelected>>', self.market_selected)
        frame.pack(side = TOP, fill = X, expand = False)
        Button(frame, text = 'Refresh', command = self.refresh_markets).pack(side = LEFT, padx = 5, pady = 5)

        # Options
        self.options_frame = Frame(self.master, width = 150)
        self.options_frame.pack(side = LEFT, fill = Y, expand = False)

        # Market information
        frame = LabelFrame(self.options_frame, text = 'Information')
        Label(frame, text = 'Total matched: ').grid(row = 0, column = 0, padx = 2, pady = 5, sticky = W)
        Label(frame, textvariable = self.info_total).grid(row = 0, column = 1, padx = 5, pady = 2, sticky = W)
        Label(frame, text = 'Pre-race: ').grid(row = 1, column = 0, padx = 5, pady = 2, sticky = W)
        Label(frame, textvariable = self.info_prerace).grid(row = 1, column = 1, padx = 5, pady = 2, sticky = W)
        Label(frame, text = 'Inplay: ').grid(row = 2, column = 0, padx = 5, pady = 2, sticky = W)
        Label(frame, textvariable = self.info_inplay).grid(row = 2, column = 1, padx = 5, pady = 2, sticky = W)
        Label(frame, text = 'Profit: ').grid(row = 3, column = 0, padx = 5, pady = 2, sticky = W)
        Label(frame, textvariable = self.info_profit).grid(row = 3, column = 1, padx = 5, pady = 2, sticky = W)
        frame.pack(side = TOP, fill = X, padx = 10, pady = 5)

        # Notes
        frame = LabelFrame(self.options_frame, text = 'Notes')
        frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        self.notes_text = Text(frame, width = 20, height = 5)
        self.notes_text.pack(side = TOP, fill = X, padx = 5, pady = 5)
        Button(frame, text = 'Save', command = self.save_notes).pack(side = TOP, anchor = SE, padx = 5, pady = 5)

        # Runners
        self.runner_frame = LabelFrame(self.options_frame, text = 'Runners')
        self.runner_frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        #Label(self.runner_frame, text = 'Select event').pack(side = TOP)

        # Runner info
        frame = LabelFrame(self.options_frame, text = 'Runner info')
        frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(frame, text = 'Relative volume', variable = self.option_plot, value = 'Relative', command = self.update_info_plot).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = 'Matched volume', variable = self.option_plot, value = 'Matched', command = self.update_info_plot).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = 'Matched smoothed', variable = self.option_plot, value = 'MatchedSmooth', command = self.update_info_plot).pack(side = TOP, anchor = W)

        # Price
        frame = LabelFrame(self.options_frame, text = 'Price')
        frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(frame, text = 'Spread', variable = self.option_price, value = 'Spread', command = self.update_price_plot).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = 'Back', variable = self.option_price, value = 'Back', command = self.update_price_plot).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = 'Lay', variable = self.option_price, value = 'Lay', command = self.update_price_plot).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = 'Last traded', variable = self.option_price, value = 'Traded', command = self.update_price_plot).pack(side = TOP, anchor = W)
        Checkbutton(frame, text = 'Smoothed', variable = self.option_price_smoothed, command = self.update_price_plot).pack(side = TOP, anchor = W)

        # Scale type
        frame = LabelFrame(self.options_frame, text = 'Price scale')
        frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(frame, text = 'Logarithmic', variable = self.option_scale, value = 'Log', command = self.update_price_plot).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = 'Linear', variable = self.option_scale, value = 'Lin', command = self.update_price_plot).pack(side = TOP, anchor = W)

        # Period
        frame = LabelFrame(self.options_frame, text = 'Period')
        frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(frame, text = '4 hrs', variable = self.option_period, value = 240, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '60 mins', variable = self.option_period, value = 60, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '30 mins', variable = self.option_period, value = 30, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '10 mins', variable = self.option_period, value = 10, command = self.update_period).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = 'Inplay', variable = self.option_period, value = 0, command = self.update_period).pack(side = TOP, anchor = W)

        # Refresh
        frame = LabelFrame(self.options_frame, text = 'Refresh')
        frame.pack(side = TOP, fill = X, padx = 10, pady = 5)
        Radiobutton(frame, text = 'disable', variable = self.option_refresh, value = 0, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '1 second', variable = self.option_refresh, value = 1, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '5 seconds', variable = self.option_refresh, value = 5, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '15 seconds', variable = self.option_refresh, value = 15, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '30 seconds', variable = self.option_refresh, value = 30, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Radiobutton(frame, text = '60 seconds', variable = self.option_refresh, value = 60, command = self.auto_refresh).pack(side = TOP, anchor = W)
        Button(frame, text = 'Now', command = self.refresh).pack(side = TOP, anchor = SE, padx = 5, pady = 5)

        # Plots
        self.plot_frame = Frame(self.master)
        self.plot_frame.pack(side = TOP, fill = BOTH, expand = True)
        self.plot_frame.grid_rowconfigure(0, weight = 1)
        self.plot_frame.grid_rowconfigure(1, weight = 1)
        self.plot_frame.grid_rowconfigure(2, weight = 4)
        self.plot_frame.grid_rowconfigure(3, weight = 0)
        self.plot_frame.grid_columnconfigure(0, weight = 1)

        # Market volume plot
        self.market_plot_figure = matplotlib.figure.Figure(figsize = [10, 2])
        self.market_plot_canvas = FigureCanvasTkAgg(self.market_plot_figure, master = self.plot_frame)
        self.market_plot_widget = self.market_plot_canvas.get_tk_widget()
        self.market_plot_widget.grid(row = 0, column = 0, sticky = NSEW)
        self.market_plot_canvas.draw()

        # Information plot
        self.info_plot_figure = matplotlib.figure.Figure(figsize = [10, 2])
        self.info_plot_canvas = FigureCanvasTkAgg(self.info_plot_figure, master = self.plot_frame)
        self.info_plot_widget = self.info_plot_canvas.get_tk_widget()
        self.info_plot_widget.grid(row = 1, column = 0, sticky = NSEW)
        self.info_plot_canvas.draw()

        # Price plot
        self.price_plot_figure = matplotlib.figure.Figure(figsize = [10, 8])
        self.price_plot_canvas = FigureCanvasTkAgg(self.price_plot_figure, master = self.plot_frame)
        self.price_plot_widget = self.price_plot_canvas.get_tk_widget()
        self.price_plot_widget.grid(row = 2, column = 0, sticky = NSEW)
        self.price_plot_canvas.draw()
        self.price_plot_toolbar_frame = Frame(self.plot_frame)
        self.price_plot_toolbar = NavigationToolbar2Tk(self.price_plot_canvas, self.price_plot_toolbar_frame)
        self.price_plot_toolbar.pack(side = TOP, fill = BOTH, expand = False)
        self.price_plot_toolbar_frame.grid(row = 3, column = 0)
        self.price_plot_toolbar.update()

    def update_notes(self, market_id):
        market = self.db_session.query(Market).filter(Market.id == market_id).one_or_none()
        if market:
            self.notes_text.delete('1.0', END)
            self.notes_text.insert(END, market.notes if market.notes else '')

    def save_notes(self):
        market = self.db_session.query(Market).filter(Market.id == self.market_id).one_or_none()
        if market:
            market.notes = self.notes_text.get('1.0', END)
            db_session.commit()

    def update_runners(self, market_id):
        self.runners = [
            RunnerInfo(r.id, r.runner.name, r.sort_priority, r.starting_price)
            for r in self.db_session.query(MarketRunner).filter(MarketRunner.market_id == market_id)
        ]
        self.runners.sort(key = lambda r: (r.starting_price, r.sort_priority))
        for r in self.runners:
            r.selected = (r.starting_price < 10)
        for widget in self.runner_frame.winfo_children():
            widget.destroy()
        for runner in self.runners:
            Checkbutton(self.runner_frame, text = f"{runner.name} ({runner.starting_price})", variable = runner._selected, command = self.update_runners_selected).pack(side = TOP, anchor = 'w')

    def update_period(self):
        self.draw_all_graphs(self.market_id)

    def auto_refresh(self):
        secs = self.option_refresh.get()
        if secs == 0:
            if self.refresh_id:
                self.master.after_cancel(self.refresh_id)
                self.refresh_id = None
        elif not self.refresh_id:
            self.refresh_id = self.master.after(secs * 1000, self.refresh)

    def refresh(self):
        if self.refresh_id:
            self.master.after_cancel(self.refresh_id)
            self.refresh_id = None
        self.update_volume_data(self.market_id)
        self.update_market_data(self.market_id)
        self.update_info(self.market_id)
        self.draw_all_graphs(self.market_id)
        secs = self.option_refresh.get()
        if secs:
            self.refresh_id = self.master.after(secs * 1000, self.refresh)

    def update_info(self, market_id):
        market = self.db_session.query(Market).filter(Market.id == market_id).one_or_none()
        if market:
            book = market.last_inplay_book
            total = book.total_matched if book else 0
            book = market.last_prerace_book
            prerace = book.total_matched if book else 0
            if total == 0:
                total = prerace
            inplay = total - prerace
            self.info_total.set(f"£{round(total)}")
            self.info_prerace.set(f"£{round(prerace)}")
            self.info_inplay.set(f"£{round(inplay)}")
            profit = 0
            for order in market.orders:
                profit += order.profit
            self.info_profit.set(f"£{round(profit, 2)}")
            
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
            'select extract(epoch from mb.date_time - m.start_time)/60 mins, r.name, mb.inplay,'
            '   mrb.last_price_traded, mrb.back_price, mrb.lay_price, (mrb.lay_price + mrb.back_price) / 2 spread_price,'
            '   mrb.total_matched, (mrb.total_matched / mb.total_matched) * 100 percent'
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

        # Calculate differences
        data['increase'] = data['total_matched'].groupby('name').diff()

        # Calculate moving averages
        data['last_price_traded_5'] = data['last_price_traded'].groupby('name').rolling(window = 5).mean().reset_index(level = 0, drop = True)
        data['back_price_5'] = data['back_price'].groupby('name').rolling(window = 5).mean().reset_index(level = 0, drop = True)
        data['lay_price_5'] = data['lay_price'].groupby('name').rolling(window = 5).mean().reset_index(level = 0, drop = True)
        data['spread_price_5'] = data['spread_price'].groupby('name').rolling(window = 5).mean().reset_index(level = 0, drop = True)
        data['total_matched_5'] = data['total_matched'].groupby('name').rolling(window = 5).mean().reset_index(level = 0, drop = True)
        data['increase_5'] = data['increase'].groupby('name').rolling(window = 5).mean().reset_index(level = 0, drop = True)

        # Save market data
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

    def draw_plot_hline(self, ax, y, style = '--', color = '#cccccc'):
        min, max = ax.get_ylim()
        if min <=  y and max >= y:
            ax.axhline(y = y, linestyle = style, color = color)

    def draw_info_graph(self, market_id):
        # Market volume
        period = self.option_period.get()
        self.market_plot_figure.clf()
        ax = self.market_plot_figure.add_subplot()
        data = self.market_volume_data
        if period == 0:
            data = data[data['inplay'] == True]
        else:
            data = data[data['inplay'] == False]
            market = self.db_session.query(Market).get(self.market_id)
            minsToPost = round((market.start_time - dt.datetime.utcnow()).total_seconds() / 60)
            if minsToPost > 0:
                data = data.query(f"mins >= -{period + minsToPost}")
            else:
                data = data.query(f"mins >= -{period}")
        if not data.empty:
            data[['rate', 'rate_smooth', 'total_matched']].plot(ax = ax, secondary_y = ['total_matched'])
            self.draw_plot_hline(ax, 500)
            self.draw_plot_hline(ax, 1000)
            self.draw_plot_hline(ax, 2500)
        ax.legend(loc = 'upper left')
        self.market_plot_canvas.draw()

        # Runner info
        self.info_plot_figure.clf()
        ax = self.info_plot_figure.add_subplot()
        plot = self.option_plot.get()
        data = self.market_data
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
                market = self.db_session.query(Market).get(self.market_id)
                minsToPost = round((market.start_time - dt.datetime.utcnow()).total_seconds() / 60)
                if minsToPost > 0:
                    data = data.query(f"mins >= -{period + minsToPost}")
                else:
                    data = data.query(f"mins >= -{period}")
            if not data.empty:
                column = 'percent'
                if plot == 'Matched':
                    column = 'increase'
                if plot == 'MatchedSmooth':
                    column = 'increase_5'
                data[column].unstack().plot(ax = ax)
        ax.legend(loc = 'upper left')
        self.info_plot_canvas.draw()

    def draw_price_graph(self, market_id):
        self.price_plot_figure.clf()
        ax = self.price_plot_figure.add_subplot()
        data = self.market_data
        runners_selected = []
        for runner in self.runners:
            if runner.selected:
                runners_selected.append(runner.name)
        if runners_selected:
            data = data.iloc[data.index.isin(runners_selected, level = 'name')]
            period = self.option_period.get()
            plot = self.option_plot.get()
            scale = self.option_scale.get()
            price = self.option_price.get()
            if period == 0:
                data = data[data['inplay'] == True]
                data = data[data['last_price_traded'] <= 25]
            else:
                data = data[data['inplay'] == False]
                market = self.db_session.query(Market).get(self.market_id)
                minsToPost = round((market.start_time - dt.datetime.utcnow()).total_seconds() / 60)
                if minsToPost > 0:
                    data = data.query(f"mins >= -{period + minsToPost}")
                else:
                    data = data.query(f"mins >= -{period}")
            if not data.empty:
                column = 'last_price_traded'
                if price == 'Back':
                    column = 'back_price'
                elif price == 'Lay':
                    column = 'lay_price'
                elif price == 'Spread':
                    column = 'spread_price'
                if self.option_price_smoothed.get():
                    column += '_5'
                data[column].unstack().plot(ax = ax, logy = (scale == 'Log'))
            for index, row in self.market_orders.iterrows():
                if row['name'] in runners_selected:
                    if row['side'] == 'BACK':
                        ax.plot([index], [row['price_matched']], 'v', markersize = 12, markerfacecolor = '#d0dfda', markeredgecolor = 'black')
                        ax.annotate(f"{round(row['size'])}", xy = (index, row['price_matched']), textcoords = 'offset pixels', xytext = (-8, 12))
                    else:
                        ax.plot([index], [row['price_matched']], '^', markersize = 12, markerfacecolor = '#efcbde', markeredgecolor = 'black')
                        ax.annotate(f"{round(row['size'])}", xy = (index, row['price_matched']), textcoords = 'offset pixels', xytext = (-7, -25))
        self.draw_plot_hline(ax, 2)
        self.draw_plot_hline(ax, 3)
        self.draw_plot_hline(ax, 4)
        self.draw_plot_hline(ax, 6)
        self.draw_plot_hline(ax, 10)
        ax.legend(loc = 'upper left')
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
