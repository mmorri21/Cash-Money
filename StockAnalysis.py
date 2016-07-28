from __future__ import division
import pandas as pd
import operator
import time
from scipy.stats import linregress
from datetime import date

start_time = time.time()

close_str = 'Close'
open_str = 'Open'
return_str = 'return'
num_stocks = 3000 # number of stocks to include in analysis. Will be limited to number of stocks in dataset
num_days = 5 # Number of market days from present to look backwards to include in "recent return" history
start = date(2016, 1, 1)
end = date.today()

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
        df[return_str] = df.apply(lambda row: return_rate(row[close_str], row[open_str]), axis = 1)
        df['ticker'] = ticker
        df['Date'] = pd.to_datetime(df['Date'])
    
    return df

def return_rate(open_amt, close_amt):
    return 100*(close_amt - open_amt)/close_amt

def flag(beta, history, recent, stdev, mean):
    # Flags stocks of interest based on defined criteria
    y = 1
    
    criteria = {beta: '<1',
                history: '>1', # should this be removed?  This is for all history, but time period is variable.  Mean seems to address this.
                recent: '<-1',
                stdev: '<2.5',
                mean: '>0.05'}

    operations = {'<': operator.lt,
                  '>': operator.gt}
                
    for key, value in criteria.iteritems():
        if not operations[value[0]](key, float(value[1:])):
            y = 0
            break

    return y

# Initiate empty data structures to be populated
df = pd.DataFrame()
output = pd.DataFrame()
missing_tickers = []

# Define parameters
df_tickers = pd.read_csv("http://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download")
df_tickers = df_tickers.append(pd.read_csv("http://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"))
tickers = df_tickers['Symbol'][:num_stocks].drop_duplicates().reset_index(drop = True)
#tickers = ['NAV', 'PCAR', 'VOLV-B.ST', 'DAI.DE', 'CAT']

# Get Data
data = tickers.apply(lambda x: get_data(x, start, end))

# Get S&P500 data for benchmark
sp500 = get_data('^GSPC', start, end)

# Create output dataframe with information about each ticker for the time period selected
for d in data:
    try: # If d is Nonetype
        if len(d) >= num_days + 5:
            df = df.append(d.merge(sp500[['Date', return_str]].rename(columns = {return_str: 'sp500return'}), how = 'inner', on = 'Date'))# keep only dates that match (different stock exchanges have different days off
    except:
        Exception

output['ticker'] = df['ticker'].unique()
output['beta'] = output.apply(lambda row: linregress(df[df['ticker'] == row['ticker']]['sp500return'],
                                                      df[df['ticker'] == row['ticker']][return_str])[0], axis = 1)
output['historical_return'] = output.apply(lambda row: return_rate(df[df['ticker'] == row['ticker']].tail(1).reset_index()[open_str][0],
                                                                    df[df['ticker'] == row['ticker']].ix[num_days, close_str]), axis = 1)
output['recent_return'] = output.apply(lambda row: return_rate(df[df['ticker'] == row['ticker']].ix[num_days - 1, open_str],
                                                                df[df['ticker'] == row['ticker']].ix[0, close_str]), axis = 1)

# Add summary statistics of each stock's historical rate of return
grouped = df[df['Date'] != max(df['Date'])].groupby('ticker')[return_str]
stats = {'mean': grouped.mean().reset_index(),
         'stdev': grouped.std().reset_index()}
for key, value in stats.iteritems():
    output = output.merge(value.rename(columns = {return_str: key}), how = 'inner', on = 'ticker')

# Compare historical rates of return vs. recent
output['flag'] = output.apply(lambda row: flag(row['beta'], row['historical_return'], row['recent_return'], row['stdev'], row['mean']), axis = 1)
output.to_csv(r'C:/Users/MAtt/Desktop/output.csv', index = False)

end_time = time.time()
time_seconds = end_time - start_time
print 'The program took ' + str(time_seconds/60) + ' minutes.'
