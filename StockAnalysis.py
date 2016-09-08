### ============================================
### IMPORT PACKAGES
### ============================================

from __future__ import division
import pandas as pd
import operator
import math
import csv
import time
import plotly
import plotly.plotly as py
import plotly.graph_objs as go
from scipy.stats import linregress
from datetime import datetime, date, timedelta

### ============================================
### DEFINE VARIABLES
### ============================================

start_time = time.time()
close_str = 'Close'
open_str = 'Open'
return_str = 'return'
history_str = 'historical_return'
recent_str = 'recent_return'
percent_str = 'percentage_of_original'
num_stocks = 7000 # number of stocks to include in analysis. Will be limited to number of stocks in dataset
num_days = 3 # Number of market days from present to look backwards to include in "recent return" history
history_days = 240 # Number of calendar days from present to look backwards to include in "historical return" history
start = date.today() - timedelta(days = history_days)
end = date.today()
flag_value = 1
num_top_stocks = 5

# Initiate empty data structures to be populated
output = pd.DataFrame(columns = ['ticker', 'beta', history_str, recent_str, 'stdev', 'mean', 'flag', 'score'])
missing_tickers = []

### ============================================
### DEFINE FUNCTIONS
### ============================================

def to_unix_time(dt):
    dt = datetime.combine(dt, datetime.min.time()) # need to convert to datetime for future operations
    epoch =  datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds() * 1000

def get_data(ticker, start, end):
    
    global missing_tickers
    df = None

    # Gets stock data from web
    try:
        # Creates Google Finance url
        url = '''http://www.google.com/finance/historical?q=''' + ticker.replace('^', '-') + '''&startdate=''' + start.strftime("%B")[:3]
        url += '''%20''' + str(start.day) + ''',%20''' + str(start.year) + '''&enddate=''' + end.strftime("%B")[:3] + '''%20'''
        url += str(end.day) + ''',%20''' + str(end.year) + '''&output=csv'''
        
        df = pd.read_csv(url).rename(columns = {'\xef\xbb\xbfDate': 'Date'})
        df[open_str] = pd.to_numeric(df[open_str], errors = 'coerce')
        df[close_str] = pd.to_numeric(df[close_str], errors = 'coerce')
    except:
        try:
            # Creates yahoo finance url
            url = '''http://ichart.finance.yahoo.com/table.csv?s=''' + ticker + '''&a=''' + str(start.month - 1)
            url += '''&b=''' + "%02d" % start.day + '''&c=''' + str(start.year) + '''&d=''' + str(end.month - 1)
            url += '''&e=''' + "%02d" % end.day + '''&f=''' + str(end.year) + '''&g=d&ignore=.csv'''
            df = pd.read_csv(url).rename(columns = {close_str: 'Non Adjust Close', 'Adj Close': close_str})            
        except:
            missing_tickers.append(ticker)

    if (df is not None) and (len(df) > 0):
        df[return_str] = df.apply(lambda row: return_rate(row[open_str], row[close_str]), axis = 1)
        df['ticker'] = ticker
        df['Date'] = pd.to_datetime(df['Date'])
    
    return df

def return_rate(open_amt, close_amt):
    return 100*(close_amt - open_amt)/close_amt

def flag(beta, history, recent, stdev, mean):
    # Flags stocks of interest based on defined criteria
    y = flag_value
    
    criteria = {beta: '<1',
                history: '>-5', # should this be removed?  This is for all history, but time period is variable.  Mean seems to address this.
                recent: '<-5',
                stdev: '<2.5',
                mean: '>0.05'}

    operations = {'<': operator.lt,
                  '>': operator.gt}
                
    for key, value in criteria.iteritems():
        if not operations[value[0]](key, float(value[1:])):
            y = 0
            break

    return y

def score(beta, history, recent, stdev, mean):
    # Gives a score based on various metrics.  The higher the score, the higher recommendation it gets.  This is all very arbitarily
    # based on a linear regression run on some manual input scores for past stocks based on my preferences.
    return beta*2.50 + history*0.09 - recent*0.30 - stdev*0.78 + mean*1.15

### ============================================
### RUN ANALYSIS
### ============================================

# Define parameters
df_tickers = pd.read_csv("http://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download")
df_tickers = df_tickers.append(pd.read_csv("http://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"))
tickers = df_tickers['Symbol'][:num_stocks].drop_duplicates().reset_index(drop = True)
del df_tickers #cleanup

# Get S&P500 data for benchmark
sp500 = get_data('^GSPC', start, end)

# Get Data
for t in tickers:
    d = {} # reset
    data = get_data(t, start, end)

    if data is not None:
        if len(data) >= num_days * 2:
            data = data.merge(sp500[['Date', return_str]].rename(columns = {return_str: 'sp500return'}), how = 'inner', on = 'Date')# keep only dates that match (different stock exchanges have different days off

            d['ticker'] = t
            d['beta'] = linregress(data['sp500return'], data[return_str])[0]
            d[history_str] = return_rate(data.tail(1).iloc[0][open_str], data.ix[num_days, close_str])
            d[recent_str] = return_rate(data.ix[num_days - 1, open_str], data.ix[0, close_str])

            # Add summary statistics of each stock's historical rate of return
            grouped = data.tail(len(data) - num_days).groupby('ticker')[return_str]
            d['mean'] = grouped.mean().iloc[0]
            d['stdev'] = grouped.std().iloc[0]

            output = output.append(d, ignore_index = True)

# Compare historical rates of return vs. recent
output['flag'] = output.apply(lambda row: flag(row['beta'], row[history_str], row[recent_str], row['stdev'], row['mean']), axis = 1)
output = output[output['flag'] == flag_value]
output['score'] = output.apply(lambda row: score(row['beta'], row[history_str], row[recent_str], row['stdev'], row['mean']), axis = 1)
output.sort_values(by = 'score', ascending = False, inplace = True)

### ============================================
### OUTPUT TO PLOTS
### ============================================

output.to_csv(r'C:/Users/Matt/Documents/Financial/output.csv', index = False)

# Create time-series plots of top stocks.
plotly.tools.set_credentials_file(username = 'mmorri21', api_key = '8e6q82a8iz')
tickers = output.iloc[:num_top_stocks]['ticker']
figure = plotly.tools.make_subplots(rows = num_top_stocks,
                                    cols = 1,
                                    shared_xaxes = True,
                                    vertical_spacing = 0.1)
data_lst = []
miny = 100
maxy = 0
missing_data = []

for t in tickers:
    
    try: # occassionally Google will start blocking requests by this point in the script
        data = get_data(t, date(1980, 1, 1), end)
        
        first_date = None
        count = 0
        while first_date is None:
            x = data[data['Date'] == start + timedelta(days = count)]
            if len(x) > 0:
                first_date = x['Date'].iloc[0]
            count += 1
            
        data[percent_str] = 100 * data[close_str] / data[data['Date'] == first_date].iloc[0][close_str]
        data['hover_text'] = 'Volume: ' + data['Volume'].astype(str) + ',\n' + 'Open: $' + data[open_str].astype(str) + ',\n' + 'Close: $' + data[close_str].astype(str)
        curRange = data[(data['Date'] <= end) & (data['Date'] >= start)]
        curMax = curRange[percent_str].max()
        curMin = curRange[percent_str].min()
        if curMax > maxy:
            maxy = curMax
        if curMin < miny:
            miny = curMin    
        data = go.Scatter(x = data['Date'],
                        y = data[percent_str],
                        line = {'width': 2.5},
                        mode = 'lines',
                        name = t,
                        text = data['hover_text'])
        data_lst.append(data)
    except:
        missing_data.append(t)
    
# Floor min and ceiling max y values to nearest increment of 5 (for plotting purposes)
miny = int(math.floor(miny / 5.0)) * 5
maxy = int(math.ceil(maxy / 5.0)) * 5

layout = go.Layout(title = 'Top ' + str(num_top_stocks) + ' Stocks for ' + str(date.today()),
                   font = {'family': 'Cambria',
                           'size': 15},
                   xaxis = {'title': 'Date',
                            'range': [to_unix_time(start), to_unix_time(end + timedelta(days = 1))]},
                   yaxis = {'title': '% of ' + str(start) + ' Close Price',
                            'ticksuffix': '%',
                            'range': [miny, maxy]},
                   hovermode = 'closest')
figure = go.Figure(data = data_lst, layout = layout)                        
py.plot(figure, filename = 'top_stocks')

# Add today's picks to history.
output['start_date'] = start
output['end_date'] = end
output['recent_days'] = num_days
output = output[['ticker',
                 'beta',
                 history_str,
                 recent_str,
                 'stdev',
                 'mean',
                 'score',
                 'start_date',
                 'end_date',
                 'recent_days']]

fd = open('C:\Users\Matt\Documents\Financial\StockAnalysis\stock_history.csv', 'a')
writer = csv.writer(fd, delimiter = ',', lineterminator = '\n')
for row in output.itertuples():
    writer.writerow(row[1:])
fd.close()

end_time = time.time()
time_seconds = end_time - start_time
print 'The program took ' + str(time_seconds/60) + ' minutes to complete.'
if len(missing_data) > 0:
    print 'The following stocks would be recommended, but data retrieval was blocked by Google: ' + str([x for x in missing_data]).strip('[').strip(']')