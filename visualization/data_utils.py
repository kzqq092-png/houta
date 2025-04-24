import pandas as pd
import numpy as np
from datetime import datetime

class DataUtils:
    def __init__(self):
        self.data = None
        
    def load_data(self, data):
        """Load and prepare data for analysis"""
        if isinstance(data, pd.DataFrame):
            self.data = data
        else:
            # Convert to DataFrame if needed
            self.data = pd.DataFrame({
                'datetime': [d.datetime for d in data],
                'open': [d.open for d in data],
                'high': [d.high for d in data],
                'low': [d.low for d in data],
                'close': [d.close for d in data],
                'volume': [d.volume for d in data]
            })
            self.data.set_index('datetime', inplace=True)
        return self.data
        
    def calculate_indicators(self):
        """Calculate common technical indicators"""
        if self.data is None:
            return None
            
        df = self.data.copy()
        
        # Calculate Simple Moving Average (SMA)
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Calculate Relative Strength Index (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        return df
        
    def get_signals(self, df=None):
        """Generate trading signals based on indicators"""
        if df is None:
            df = self.calculate_indicators()
            
        signals = pd.DataFrame(index=df.index)
        signals['signal'] = 0
        
        # Generate signals based on SMA crossover
        signals.loc[df['sma_20'] > df['sma_50'], 'signal'] = 1
        signals.loc[df['sma_20'] < df['sma_50'], 'signal'] = -1
        
        # Add RSI overbought/oversold signals
        signals.loc[df['rsi'] > 70, 'signal'] = -1
        signals.loc[df['rsi'] < 30, 'signal'] = 1
        
        return signals 