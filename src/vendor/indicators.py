import pandas as pd
import numpy as np
from config import *
#----------------------------------------------------------------------------------------------------------------------  
if not CALC_MANUALLY:
  import pandas_ta as ta
  from   ta.trend import MACD
  from   ta.momentum import StochasticOscillator
#----------------------------------------------------------------------------------------------------------------------  
def calcWeeklyFromDaily(df):
  #### RESAMPLING TO WEEKLY TO CLEAN NOISE
  agg_dict = {
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'# sum, mean
  }
  # resample dataframe from daily to weekly and use as date the first day of the week
  df_agg = df.resample('W').agg(agg_dict)
  df_agg.index = df_agg.index - pd.Timedelta(days=df_agg.index.dayofweek.min())
  return df_agg
#----------------------------------------------------------------------------------------------------------------------  
def addStochasticOscillator(df, periods=14, smooth=3):
    copy      = df.copy()
    high_roll = copy["High"].rolling(periods).max()
    low_roll  = copy["Low"].rolling(periods).min()
    # Fast stochastic indicator
    num = copy["Close"] - low_roll
    denom = high_roll - low_roll
    copy["%K"] = (num / denom) * 100
    # Slow stochastic indicator
    copy["%D"] = copy["%K"].rolling(smooth).mean()
    return copy
  
def calcStochastic(df):
  # stochastic
  # see https://school.stockcharts.com/doku.php?id=technical_indicators:stochastic_oscillator_fast_slow_and_full
  #   k = (close - lowest_n) / (highest_n - lowest_n) * 100
  #   d = moving average of k for a window w 
  #   w = window size 
  #   n = number of days
  # make standard fast stochastic calculation 14, 3
  if CALC_MANUALLY:
    if True:
      s=16
      w=3
      stoch = addStochasticOscillator(df,s,w)
      # make slow Stochastic Oscillator with standard window 3
      df['stoch_k'] = stoch["%D"]
      df['stoch_k_signal'] = stoch["%K"]
      # make average of stochastic k and signal
      # 20, 5; 15, 12; 18, 14
      #df['StMa'] = df['stoch_k'].rolling(window=12).mean()
      #df['StMaS'] = df['stoch_k_signal'].rolling(window=9).mean()
      stoch = addStochasticOscillator(df,44,5)
      df['StMa'] = stoch["%D"]
      df['StMaS'] = stoch["%K"]
    else:
      stoch = addStochasticOscillator(df)
      # make slow Stochastic Oscillator with standard window 3
      df['stoch_k'] = stoch["%D"]
      df['stoch_k_signal'] = stoch["%K"]
      # make average of stochastic k and signal
      # 20, 5; 15, 12; 18, 14
      df['StMa'] = df['stoch_k'].rolling(window=12).mean()
      df['StMaS'] = df['stoch_k_signal'].rolling(window=9).mean()
  else:
    if True:
      s=16
      w=3
      stoch = StochasticOscillator(high=df['High'], close=df['Close'], low=df['Low'], window=s-w+1,  smooth_window=w)
      # make slow Stochastic Oscillator with standard window 3
      df['stoch_k'] = stoch.stoch().rolling(window=3).mean()
      df['stoch_k_signal'] = stoch.stoch_signal().rolling(window=3).mean()
      s=44 
      w=6
      stoch = StochasticOscillator(high=df['High'], close=df['Close'], low=df['Low'], window=s-w+1,  smooth_window=w)
      df['StMa'] = stoch.stoch().rolling(window=w).mean()
      df['StMaS'] = stoch.stoch_signal().rolling(window=5).mean()
    else:
      stoch = StochasticOscillator(high=df['High'], close=df['Close'], low=df['Low'], window=14,  smooth_window=3)
      # make slow Stochastic Oscillator with standard window 3
      df['stoch_k'] = stoch.stoch().rolling(window=3).mean()
      df['stoch_k_signal'] = stoch.stoch_signal().rolling(window=3).mean()
      # make average of stochastic k and signal
      # 20, 5; 15, 12; 18, 14
      df['StMa'] = stoch.stoch().rolling(window=12).mean()
      df['StMaS'] = stoch.stoch_signal().rolling(window=9).mean()
      #df[f'StMa'] = stoch.stoch().rolling(window=15).mean() - (df['stoch_k']- df['stoch_k_signal']).rolling(window=10).mean()
      #.rolling(window=15).mean() # 20, 5
      #df['stoch_k_signal'] += delta
  return df
#----------------------------------------------------------------------------------------------------------------------  
def calcMacd(df):
  """Calculate RSI with Exponential Moving Average
  Adds following entries to df: Macd, MacdSig, MacdDiff
  """
  # MACD
  #   MACD calculation
  #   MACD        = EMA(close, timeperiod=12) - EMA(close, timeperiod=26)
  #   MACD signal = EMA(MACD_slow, timeperiod=9)
  #   Histogram   = MACD_slow - MACD_signal 
  #   commonly used (fast, slow, smooth) = (26, 12, 9)
  # slow, fast, smooth = 29, 10, 6
  slow, fast, smooth = 26, 12, 9
  if CALC_MANUALLY:
    exp1   = df['Close'].ewm(span = fast, adjust = False).mean()
    exp2   = df['Close'].ewm(span = slow, adjust = False).mean()
    macd   = pd.DataFrame(exp1 - exp2).rename(columns = {'Close':'Macd'})
    signal = pd.DataFrame(macd.ewm(span = smooth, adjust = False).mean()).rename(columns = {'Macd':'MacdSignal'})
    hist   = pd.DataFrame(macd['Macd'] - signal['MacdSignal']).rename(columns = {0:'hist'})
    df['Macd']    = macd
    df['MacdSig'] = signal
    df['MacdDif'] = hist.rename(columns = {0:'MacdDif'})
  else:
    macd = MACD(close=df['Close'], window_slow=slow, window_fast=fast, window_sign=smooth)
    df['Macd'] = macd.macd()
    df['MacdSig'] = macd.macd_signal()
    df['MacdDif'] = macd.macd_diff()
  return df
#----------------------------------------------------------------------------------------------------------------------  
def calcRsi(df):
  """Calculate RSI with Exponential Moving Average
  Adds following entries to df: RSI
  """
  # calculate RSI with Exponential Moving Average
  if CALC_MANUALLY:  
    # see https://www.learnpythonwithrune.org/pandas-calculate-the-relative-strength-index-rsi-on-a-stock/
    delta     = df['Close'].diff()
    up        =    delta.clip(lower=0)
    down      = -1*delta.clip(upper=0)
    ema_up    = up  .ewm(com=10, adjust=False).mean()
    ema_down  = down.ewm(com=7, adjust=False).mean()
    rs        = ema_up/ema_down
    df['RSI'] = 100 - (100/(1 + rs))
  else:
    # Concatenate all statistics to one big matrix
    rsi = df.ta.rsi(close='close', length=14, drift=0)
    df['RSI'] = rsi
    #df = pd.concat([df, rsi], axis=1)  
  return df
#----------------------------------------------------------------------------------------------------------------------  
def calcMovingAverages(df):
  """Calculate the Moving averages to df.
  Adds following entries to df: Ma#, Cma#, Ema# with # = 5,10,20,50,100,200
  """
  # moving averages 5 to 100 days
  averages = [5, 10, 20, 50, 100, 200]
  for avg in averages:
    df[f'Ma{avg}'] = df['Close'].rolling(window=avg).mean()
    df[f'Cma{avg}'] = df['Close'].expanding().mean()
    df[f'Ema{avg}'] = df['Close'].ewm(span=avg).mean()
    #df[f'Ema{avg}'] = ta.ema(df['Close'], avg)
  return df
#----------------------------------------------------------------------------------------------------------------------  
def calcBollingerBands(df,n=20,m=2):
  """Calculate the Bollinger Bands for the given dataframe.
  Adds following entries to df. Ma20, BbUpper, BbLower
  """
  if 0:
    # from https://tcoil.info/compute-bollinger-bands-for-stocks-with-python-and-pandas/
    # takes dataframe on input
    # n = smoothing length
    # m = number of standard deviations away from MA
    if 0:
      #typical price
      data = (df['High'] + df['Low'] + df['Close']) / 3
    else:
      data = df['Close']    
    # takes one column from dataframe
    B_MA = pd.Series((data.rolling(n, min_periods=n).mean()), name='B_MA')
    sigma = data.rolling(n, min_periods=n).std() 
    BU = pd.Series((B_MA + m * sigma), name='BU')
    BL = pd.Series((B_MA - m * sigma), name='BL')    
    #df = df.join(B_MA)
    df['BbUpper'] = BU
    df['BbLower'] = BL

  else:    
  # from https://medium.com/geekculture/implementing-the-most-popular-indicator-on-tradingview-using-python-239d579412ab
  # parameter setup (default values in the original indicator)
    length    = n
    mult      = m
    # moving average
    m_avg = df[f'Ma{length}']
    # standard deviation
    m_std = df['Close'].rolling(window=length).std(ddof=0)
    # upper Bollinger Bands
    df['BbUpper'] = m_avg + mult * m_std
    # lower Bollinger Bands 
    df['BbLower'] = m_avg - mult * m_std
    df['BbSize'] = df['BbUpper'] - df['BbLower']
  return df
#----------------------------------------------------------------------------------------------------------------------  
def calcVolatility(df):
  # from https://www.learnpythonwithrune.org/calculate-the-volatility-of-historic-stock-prices-with-pandas-and-python/
  df['Vola'] = np.log(df['Close']/df['Close'].shift()).std()*252**.5*100
  return df
#----------------------------------------------------------------------------------------------------------------------  
def calcSize(df, i, past):
    return  df['Close'].iloc[i] - df['Open'].iloc[i-past]
#----------------------------------------------------------------------------------------------------------------------  
def calcMl(df):
  return ml.calculate(df)
#----------------------------------------------------------------------------------------------------------------------  
def calculateIndicators(df):
  """Calculate the indicators for the given dataframe df."""
  df = calcStochastic(df)
  df = calcMacd(df)
  df = calcMovingAverages(df)
  df = calcBollingerBands(df)
  df = calcRsi(df)
  df = calcVolatility(df)
  #df = calcMl(df)
  return df
#----------------------------------------------------------------------------------------------------------------------  
#----------------------------------------------------------------------------------------------------------------------  
def isRising(df, i):
  return df['Open'].iloc[i] < df['Close'].iloc[i] or df['Close'].iloc[i] > df['Close'].iloc[i-1]
#----------------------------------------------------------------------------------------------------------------------  
def isFalling(df, i):
  return df['Close'].iloc[i] < df['Open'].iloc[i] #or df['Close'].iloc[i] < df['Close'].iloc[i-1]
#----------------------------------------------------------------------------------------------------------------------  
def isHighAboveUpperBoellingerBand(df, i):
  return df['High'].iloc[i] > df['BbUpper'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isOpenAboveUpperBoellingerBand(df, i):
  return df['Open'].iloc[i] > df['BbUpper'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isCloseAboveUpperBoellingerBand(df, i):
  return df['Close'].iloc[i] > df['BbUpper'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isOpenBelowUpperBoellingerBand(df, i):
  return df['Open'].iloc[i] < df['BbUpper'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isCloseBelowUpperBoellingerBand(df, i):
  return df['Close'].iloc[i] < df['BbUpper'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isCloseAboveUpperBoellingerBand(df, i):
  return df['Close'].iloc[i] >= df['BbUpper'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isOpenBelowLowerBoellingerBand(df, i):
  return df['Open'].iloc[i] < df['BbLower'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isOpenAboveLowerBoellingerBand(df, i):
  return df['Open'].iloc[i] > df['BbLower'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isCloseBelowLowerBoellingerBand(df, i):
  return df['Close'].iloc[i] < df['BbLower'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isCloseAboveLowerBoellingerBand(df, i):
  return df['Close'].iloc[i] > df['BbLower'].iloc[i]  
#----------------------------------------------------------------------------------------------------------------------  
def isRsiBelow(val, df, i):
  return df['RSI'].iloc[i] < val 
#----------------------------------------------------------------------------------------------------------------------  
def isRsiAbove(val,df, i):
  return df['RSI'].iloc[i] > val 
#----------------------------------------------------------------------------------------------------------------------  
def isStochasticSlowAbove(val,df, i):
  return df['StMa'].iloc[i] > val 
#----------------------------------------------------------------------------------------------------------------------  
def isStochasticSlowBelow(val,df, i):
  return df['StMa'].iloc[i] < val 
#----------------------------------------------------------------------------------------------------------------------  
def isCrossStochasticDown(df, i):
    return df['StMaS'].iloc[i] < df['StMa'].iloc[i] and df['StMaS'].iloc[i-1] >= df['StMa'].iloc[i-1]
#----------------------------------------------------------------------------------------------------------------------  
def isCrossStochasticUp(df, i):
  choice = 2
  if choice == 1:
    return df['StMaS'].iloc[i] > df['StMa'].iloc[i]
  elif choice == 2:
    return df['StMaS'].iloc[i] > df['StMa'].iloc[i] and df['StMaS'].iloc[i-1] <= df['StMa'].iloc[i-1]
  elif choice == 3:
    return df['stoch_k_signal'].iloc[i] > df['stoch_k'].iloc[i] and df['stoch_k_signal'].iloc[i-1] <= df['stoch_k'].iloc[i-1]
  return True
#----------------------------------------------------------------------------------------------------------------------  
def isMacdRising(df, i):
    return df['MacdDif'].iloc[i-1] < df['MacdDif'].iloc[i]
#----------------------------------------------------------------------------------------------------------------------  
def isMacdFalling(df, i):
    return df['MacdDif'].iloc[i-1] > df['MacdDif'].iloc[i]
#----------------------------------------------------------------------------------------------------------------------  
def isCrossEma50Ema200Up(df, i):
  return ((df['Ema50'].iloc[i-1] <= df['Ema200'].iloc[i-1]) and (df['Ema50'].iloc[i] >= df['Ema200'].iloc[i]))
#----------------------------------------------------------------------------------------------------------------------  
def isCrossEma50Ema200Down(df, i):
  return ((df['Ema50'].iloc[i-1] >= df['Ema200'].iloc[i-1]) and (df['Ema50'].iloc[i] <= df['Ema200'].iloc[i]))