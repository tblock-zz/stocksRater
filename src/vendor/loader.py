import pandas as pd
import yfinance as yf
from   datetime import datetime 

from curl_cffi import requests
session = requests.Session(impersonate="chrome")

from config import *
import globals
from indicators import *
#------------------------------------------------------------------------------
try:
  import IbkrTws as ib
  globals.HAS_IBKR = True
except:
  globals.HAS_IBKR = False
#------------------------------------------------------------------------------
FILE_FORMAT     = 'parquet'    # csv or parquet
globals.WORK_WITH_FILES = False    # Load from file and not from internet to speed up processing
#------------------------------------------------------------------------------
def fromNet(symbol, prd, intrvl='1d'):
  """load the ticker data from yahoo finance for the given period
  we use the interval of 1 day
  """
  df = pd.DataFrame() # Empty DataFrame
  # Request historic pricing data
  if globals.HAS_IBKR and ib.isOpen():
    try:
      df = ib.get(symbol)
    except Exception as e:
      print(f"Error fetching data from IBKR: {e}")  
  else:
    ticker = yf.Ticker(symbol, session=session)
    # Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
    df = ticker.history(period=prd, interval=intrvl)[['Open', 'Close', 'Low', 'High', 'Volume']]
  # interval one week
  #df = df.ta.ticker(symbol, period=prd, interval="1wk")
  if df.empty:
    raise globals.CustomError("No data")
  return df
#------------------------------------------------------------------------------
def readFromFile(symbol):
  """read ticker values from the file data/{symbol}.parquet"""
  df = pd.DataFrame() # Empty DataFrame
  try:
    if FILE_FORMAT == 'csv':
      fileName = f'data/{symbol}.csv'
      df = pd.read_csv(fileName, index_col='Date', parse_dates=True)
    else:
      fileName = f'data/{symbol}.parquet'
      df = pd.read_parquet(fileName)
  except FileNotFoundError:  
    print(f"No file found for {symbol}")
  return df
#------------------------------------------------------------------------------
def saveToFile(ticker):
  """save ticker values to the file data/{ticker}.parquet"""
  df = fromNet(ticker, '10y')
  if FILE_FORMAT == 'csv':
    fileName = f'data/{ticker}.csv'
    df.to_csv(fileName)
  else:  
    fileName = f'data/{ticker}.parquet'
    df.to_parquet(fileName)
  return df
#------------------------------------------------------------------------------
def getLastDate(df):
  if FILE_FORMAT == 'csv':
    return df.index[-1]
  else:
    return df.index[-1].to_pydatetime()  
#------------------------------------------------------------------------------
def loadTickerData(symbol,intrvl='1d'):
  """load the ticker data from the internet (globals.WORK_WITH_FILES = False) or file data/{symbol}.parquet."""
  df = pd.DataFrame() # Empty 
  if globals.WORK_WITH_FILES:
    try:
      df = readFromFile(symbol)
      last_save_date = getLastDate(df)
      current_date = datetime.now()
      diff = datetime.now() - getLastDate(df)
      #if datetime difference > one day load new data from internet
      if diff.days > 1:
        # load new data from internet
        dfNew = fromNet(symbol, f'{diff.days}d', intrvl)
        # append the new data to the existing data
        df = pd.concat([df,dfNew]).drop_duplicates().reset_index(drop=True) 
        saveToFile(symbol)                      # save the new data to the file
    except FileNotFoundError:  
      exit()
  else:
    df = fromNet(symbol, '5y',intrvl)
  df = df.sort_index()
  return df
#----------------------------------------------------------------------------------------------------------------------  
#----------------------------------------------------------------------------------------------------------------------  
