"""Import-Bruecke zu den mitgelieferten Vendor-Modulen.

Diese Paket-Version ist autark: Die kampferprobten Module aus
stocksCheck (loader, indicators, config, globals, financialData)
liegen unter src/stockscheck/vendor/ und werden von hier importiert.

- loader: yfinance-Daten laden (mit curl_cffi-Session gegen Bot-Detection)
- indicators: RSI, MACD, Stochastik, SMA, Bollinger, CrossEMA (CALC_MANUALLY=True)
- financialData: FairValue, KGV, KBV
"""
import sys
from pathlib import Path

_VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor"
if not _VENDOR_DIR.exists():
    raise ImportError(
        f"Vendor modules not found at {_VENDOR_DIR}. "
        "The package should ship src/stockscheck/vendor/ - looks incomplete."
    )

if str(_VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(_VENDOR_DIR))

# Setze CALC_MANUALLY=True bevor indicators geladen wird
import config as _stockscheck_config  # noqa: E402
_stockscheck_config.CALC_MANUALLY = True

from curl_cffi import requests as _curl_requests  # noqa: E402

# Eine geteilte Session fuer yfinance (umgeht Bot-Detection via curl_cffi)
YF_SESSION = _curl_requests.Session(impersonate="chrome")

# yfinance ist global verfuegbar (per requirements.txt)
import yfinance as yf  # noqa: E402

# Globale yf.Ticker-Wrapper, die unsere Session nutzen
def get_ticker(symbol: str):
    """Liefert yf.Ticker mit unserer Session."""
    return yf.Ticker(symbol, session=YF_SESSION)


# Re-Exports
# Registriere dieses Modul unter flat-Namen, damit die try-Imports in
# indicators.py / fundamentals.py ("from stockscheck_bridge import ...")
# ohne Package-Prefix funktionieren.

from loader import loadTickerData, fromNet, saveToFile  # noqa: E402,F401
from indicators import (  # noqa: E402,F401
    calculateIndicators,
    calcRsi, calcMacd, calcStochastic, calcMovingAverages, calcBollingerBands,
    calcWeeklyFromDaily,
    isRsiBelow, isRsiAbove, isStochasticSlowAbove, isStochasticSlowBelow,
    isCrossStochasticUp, isCrossStochasticDown,
    isMacdRising, isMacdFalling,
    isCrossEma50Ema200Up, isCrossEma50Ema200Down,
    isCloseBelowLowerBoellingerBand, isCloseAboveUpperBoellingerBand,
)
import financialData as fd  # noqa: E402,F401
from financialData import getFinancialData, calculateFairValues  # noqa: E402,F401
