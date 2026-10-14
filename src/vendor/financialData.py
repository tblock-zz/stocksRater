import pandas as pd
import yfinance as yf
#---------------------------------------------------------------------------------------------------------------------- 
def getEarningsDate(tckr):
  return tckr.calendar['Earnings Date'][0]
#---------------------------------------------------------------------------------------------------------------------- 
def calculateIntrinsicValue(stockInfo):
  totalAssets       = stockInfo.get('totalAssets', 0) or 0
  totalLiabilities  = stockInfo.get('totalLiabilities', 0) or 0
  netIncome         = stockInfo.get('netIncome', 0) or 0
  sharesOutstanding = stockInfo.get('sharesOutstanding', 0) or 1
  netAssetValue     = (totalAssets - totalLiabilities) / sharesOutstanding
  revenueGrowth     = stockInfo.get('revenueGrowth', 0.05)
  operatingMargin   = stockInfo.get('operatingMargins', 0) or 0
  intrinsicValue    = (
    netAssetValue * 0.4 +
    (netIncome / sharesOutstanding) * (1 + revenueGrowth) * 10 * 0.4 +
    (netAssetValue * operatingMargin) * 0.2
  )
  return max(intrinsicValue, netAssetValue)
#---------------------------------------------------------------------------------------------------------------------- 
def getFairValue(tckr):
  # Calculate historical PE ratio (average of the last 5 years)
    eps = tckr.info.get('trailingEps', None) # Gewinn pro Aktie (EPS)
    hist = tckr.history(period="5y")
    historical_pe = None
    hist['PE'] = hist['Close'] / eps
    historical_pe = hist['PE'].mean()
    if 0:
      # Berechnung des jährlichen KGVs
      annual_eps = tckr.earnings['Earnings']
      annual_close = hist['Close'].resample('Y').last()
      if len(annual_eps) < 5:
        print(f"Not enough earnings data")
        return    
      annual_pe = annual_close / annual_eps
      historical_pe = annual_pe.mean()
    fairValue = eps * historical_pe
    if historical_pe is None:
      return None
    return fairValue
#-------------------------------------------------------------------------------
def calculateFairValues(stockInfo, lastPrice):
    earningsPerShare = stockInfo.get('trailingEps', 0) or 0
    intrinsicValue = calculateIntrinsicValue(stockInfo)
    freeCashFlow = stockInfo.get('freeCashFlow', 0) or 0
    sharesOutstanding = stockInfo.get('sharesOutstanding', 0) or 1
    revenueGrowth = stockInfo.get('revenueGrowth', 0.05)
    fairValues = {
        'graham'    : (earningsPerShare * (8.5 + 2 * (revenueGrowth * 100))) * 4.4 / 3.7,
        'dcf'       : (freeCashFlow * (1.05 ** 5)) / sharesOutstanding / 0.1,
        'peg'       : earningsPerShare * (revenueGrowth * 100) * 15,
        'industryPe': earningsPerShare * 15,
        'gordon'    : (stockInfo.get('dividendRate', 0) or 0) / (0.1 - 0.03),
        'intrinsic' : intrinsicValue,
        'historical': 0,
    }
    validValues = [v for v in fairValues.values() if v > 0 and v < lastPrice * 5]
    fairValues['average'] = sum(validValues) / len(validValues) if validValues else None
    validValues ={key: value for key, value in fairValues.items() if value > 0}
    return validValues
#---------------------------------------------------------------------------------------------------------------------- 
def getFinancialData(tckr):
  """Returns the financial data,
    use filter = True in case only kgv<20 and kbv<3 shall be shown 
    all possible values can shown with: yfinance.ticker(ticker).info
  """
  dict = None
  try:
    info = tckr.info
    eps = info.get('trailingEps', None) # Gewinn pro Aktie (EPS)
    bv = info.get('bookValue', None)    # Buchwert pro Aktie (Book Value)
    if eps is None or bv is None:
      return
    price = info.get('currentPrice', None)
    # load the ticker kgv, kbv and fair value
    kgv = price/eps
    kbv = price/bv
    fairValues = calculateFairValues(info, price)
    fairValues['historical'] = getFairValue(tckr)
    dict = {    
      'shortName' : 0,
      'enterpriseValue' : 0,
      'totalDebt' : 0,
      'netEnterpriseValue' : 0,
      'marketCap' : 0,
      'totalCash' : 0,
      'totalRevenue' : 0,
      'freeCashflow' : 0,
      'ebitda' : 0,
      'bookValue' : 0,
      'revenuePerShare' : 0,
      'revenueGrowth' : 0,
      'grossMargins' : 0,
      'trailingAnnualDividendRate' : 0,
      'recommendationKey' : 0,
      'lastDividendDate' : 0,
      'exDividendDate' : 0,
      'earningsDate' : 0,
      'twoHundredDayAverage' : 0,
      'fiftyDayAverage' : 0,
      'targetMedianPrice' : 0,
    }
    for key in dict:
      dict[key] = info.get(key, None)
    dict['LastPrice'] = price
    dict['kgv'] = kgv
    dict['kbv'] = kbv
    dict['FairValue'] = fairValues
    # convert from unix time to datetime
    dict['lastDividendDate']   = pd.to_datetime(dict['lastDividendDate'], unit='s')
    dict['exDividendDate']     = pd.to_datetime(dict['exDividendDate'], unit='s')
    dict['earningsDate']       = pd.to_datetime(getEarningsDate(tckr))
    dict['netEnterpriseValue'] = dict['enterpriseValue'] - dict['totalDebt'] 
  # catch exception for every error
  except KeyError:
    print(f"KeyError: {KeyError}")
  finally:
    return dict 
#---------------------------------------------------------------------------------------------------------------------- 
def getFinancials2(ticker):
    import ib_async
    from ib_fundamental import get_fundamentals
    ib = ib_async.IB().connect('localhost',config.port)
#---------------------------------------------------------------------------------------------------------------------- 
