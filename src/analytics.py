"""
Analytics engine for pairs trading
Computes hedge ratio, spread, z-score, correlation, and statistical tests
"""
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class PairsAnalytics:
   
    def __init__(self):
        pass
    
    def calculate_hedge_ratio_ols(
        self,
        price_a: pd.Series,
        price_b: pd.Series
    ) -> Tuple[float, float, float]:
        # Remove NaN values
        df = pd.DataFrame({'a': price_a, 'b': price_b}).dropna()
        
        if len(df) < 2:
            return 0.0, 0.0, 0.0
        
        # Calculate using numpy for efficiency
        x = df['b'].values
        y = df['a'].values
        
        # Add constant term (intercept)
        X = np.vstack([x, np.ones(len(x))]).T
        
        # OLS: beta = (X'X)^-1 X'y
        beta, alpha = np.linalg.lstsq(X, y, rcond=None)[0]
        
        # Calculate R-squared
        y_pred = beta * x + alpha
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        return float(beta), float(alpha), float(r_squared)
    
    def calculate_rolling_hedge_ratio(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        window: int
    ) -> pd.DataFrame:
        df = pd.DataFrame({'a': price_a, 'b': price_b}).dropna()
        
        if len(df) < window:
            return pd.DataFrame()
        
        rolling_beta = []
        rolling_alpha = []
        rolling_r2 = []
        
        for i in range(window, len(df) + 1):
            window_data = df.iloc[i-window:i]
            beta, alpha, r2 = self.calculate_hedge_ratio_ols(
                window_data['a'],
                window_data['b']
            )
            rolling_beta.append(beta)
            rolling_alpha.append(alpha)
            rolling_r2.append(r2)
        
        result = pd.DataFrame({
            'beta': rolling_beta,
            'alpha': rolling_alpha,
            'r_squared': rolling_r2
        }, index=df.index[window:])
        
        return result
    
    def calculate_spread(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        hedge_ratio: Optional[float] = None
    ) -> pd.Series:
        df = pd.DataFrame({'a': price_a, 'b': price_b}).dropna()
        
        if len(df) < 2:
            return pd.Series()
        
        if hedge_ratio is None:
            hedge_ratio, _, _ = self.calculate_hedge_ratio_ols(df['a'], df['b'])
        
        spread = df['a'] - hedge_ratio * df['b']
        
        return spread
    
    def calculate_z_score(
        self,
        spread: pd.Series,
        window: int
    ) -> pd.Series:
        rolling_mean = spread.rolling(window=window).mean()
        rolling_std = spread.rolling(window=window).std()
        
        z_score = (spread - rolling_mean) / rolling_std
        
        return z_score
    
    def calculate_rolling_z_score(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        window: int
    ) -> pd.DataFrame:
        # Calculate hedge ratio
        beta, alpha, r2 = self.calculate_hedge_ratio_ols(price_a, price_b)
        
        # Calculate spread
        spread = self.calculate_spread(price_a, price_b, beta)
        
        # Calculate z-score
        z_score = self.calculate_z_score(spread, window)
        
        # Calculate rolling statistics
        rolling_mean = spread.rolling(window=window).mean()
        rolling_std = spread.rolling(window=window).std()
        
        result = pd.DataFrame({
            'spread': spread,
            'z_score': z_score,
            'rolling_mean': rolling_mean,
            'rolling_std': rolling_std,
            'beta': beta,
            'alpha': alpha,
            'r_squared': r2
        })
        
        return result
    
    def adf_test(self, series: pd.Series) -> Dict[str, float]:
        try:
            from statsmodels.tsa.stattools import adfuller
            
            # Remove NaN
            series_clean = series.dropna()
            
            if len(series_clean) < 10:
                return {
                    'adf_statistic': np.nan,
                    'p_value': np.nan,
                    'is_stationary': False,
                    'critical_values': {}
                }
            
            result = adfuller(series_clean, autolag='AIC')
            
            adf_statistic = result[0]
            p_value = result[1]
            critical_values = result[4]
            
            # Series is stationary if p-value < 0.05
            is_stationary = p_value < 0.05
            
            return {
                'adf_statistic': float(adf_statistic),
                'p_value': float(p_value),
                'is_stationary': is_stationary,
                'critical_values': {
                    '1%': float(critical_values['1%']),
                    '5%': float(critical_values['5%']),
                    '10%': float(critical_values['10%'])
                }
            }
        except Exception as e:
            logger.error(f"ADF test failed: {e}")
            return {
                'adf_statistic': np.nan,
                'p_value': np.nan,
                'is_stationary': False,
                'critical_values': {},
                'error': str(e)
            }
    
    def calculate_correlation(
        self,
        series_a: pd.Series,
        series_b: pd.Series
    ) -> float:
        df = pd.DataFrame({'a': series_a, 'b': series_b}).dropna()
        
        if len(df) < 2:
            return 0.0
        
        correlation = df['a'].corr(df['b'])
        
        return float(correlation)
    
    def calculate_rolling_correlation(
        self,
        series_a: pd.Series,
        series_b: pd.Series,
        window: int
    ) -> pd.Series:
        df = pd.DataFrame({'a': series_a, 'b': series_b}).dropna()
        
        rolling_corr = df['a'].rolling(window=window).corr(df['b'])
        
        return rolling_corr
    
    def calculate_price_statistics(
        self,
        prices: pd.Series,
        window: Optional[int] = None
    ) -> Dict[str, float]:
        prices_clean = prices.dropna()
        
        if len(prices_clean) == 0:
            return {}
        
        stats_dict = {
            'mean': float(prices_clean.mean()),
            'std': float(prices_clean.std()),
            'min': float(prices_clean.min()),
            'max': float(prices_clean.max()),
            'current': float(prices_clean.iloc[-1])
        }
        
        if window and len(prices_clean) >= window:
            returns = prices_clean.pct_change().dropna()
            rolling_vol = returns.rolling(window=window).std()
            stats_dict['rolling_volatility'] = float(rolling_vol.iloc[-1])
        
        return stats_dict
    
    def calculate_half_life(self, spread: pd.Series) -> float:
        spread_clean = spread.dropna()
        
        if len(spread_clean) < 10:
            return np.nan
        
        # Lag the spread
        spread_lag = spread_clean.shift(1).dropna()
        spread_diff = spread_clean.diff().dropna()
        
        # Align indices
        common_index = spread_lag.index.intersection(spread_diff.index)
        spread_lag = spread_lag.loc[common_index]
        spread_diff = spread_diff.loc[common_index]
        
        if len(spread_lag) < 2:
            return np.nan
        
        # OLS regression: delta_spread = lambda * spread_lag
        X = spread_lag.values.reshape(-1, 1)
        y = spread_diff.values
        
        try:
            lambda_param = np.linalg.lstsq(X, y, rcond=None)[0][0]
            
            # Half-life = -ln(2) / lambda
            if lambda_param < 0:
                half_life = -np.log(2) / lambda_param
                return float(half_life)
            else:
                return np.nan
        except:
            return np.nan
