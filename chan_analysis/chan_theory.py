# -*- coding: utf-8 -*-
"""
Chan Theory Stock Analysis Program v2.0
Based on Tushare data with visualization, multi-level analysis, and Obsidian sync

Features:
- Bi (笔), Zhongshu (中枢), Beichi (背驰) identification
- Multi-level analysis (1min, 5min, 15min, 30min, 60min, Daily, Weekly, Monthly)
- Visualization with matplotlib
- Obsidian note synchronization
- Trading signal generation

Author: XiaoZhi @ 2026-04-14
"""

import pandas as pd
import numpy as np
from datetime import datetime
import tushare as ts
import json
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import io

# ============ Config ============
TUSHARE_TOKEN = "152df786083441ef82f9cc4dca59f42312ac82e477facec01e9917f5"
CHAN_DIR = r"C:\Users\lucky\projects\my_project\chan_analysis"
OBSIDIAN_DIR = r"D:\Obsidian\股票分析\缠论分析"
PLOT_DIR = r"C:\Users\lucky\projects\my_project\chan_analysis\plots"

def get_ts_token():
    return TUSHARE_TOKEN


# ============ Tushare Data ============

def get_stock_data(ts_code, start_date, end_date, adjust="qfq"):
    """Get stock daily data"""
    pro = ts.pro_api(get_ts_token())
    
    df = pro.daily(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        adj=adjust
    )
    
    if df is None or df.empty:
        return None
    
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values('trade_date').reset_index(drop=True)
    df = df.rename(columns={'trade_date': 'date', 'ts_code': 'code'})
    
    return df


def get_stock_basic(ts_code):
    """Get stock basic info"""
    pro = ts.pro_api(get_ts_token())
    df = pro.stock_basic(ts_code=ts_code, list_status='L')
    
    if df is not None and not df.empty:
        return df.iloc[0].to_dict()
    return None


def get_minute_data(ts_code, freq='60min', start_date=None, end_date=None):
    """Get minute-level data"""
    pro = ts.pro_api(get_ts_token())
    
    if start_date is None:
        start_date = (datetime.now() - pd.Timedelta(days=5)).strftime('%Y%m%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    df = ts.pro_bar(
        ts_code=ts_code,
        adj='qfq',
        freq=freq,
        start_date=start_date,
        end_date=end_date
    )
    
    if df is None or df.empty:
        return None
    
    df['trade_time'] = pd.to_datetime(df['trade_time'])
    df = df.sort_values('trade_time').reset_index(drop=True)
    
    return df


# ============ Chan Theory Core ============

def is_fenxing(df, i, direction='top'):
    """Check if K-line i forms a fenxing (division)"""
    if i < 1 or i >= len(df) - 1:
        return False
    
    if direction == 'top':
        return (df.iloc[i]['high'] > df.iloc[i-1]['high'] and 
                df.iloc[i]['high'] > df.iloc[i+1]['high'])
    else:
        return (df.iloc[i]['low'] < df.iloc[i-1]['low'] and 
                df.iloc[i]['low'] < df.iloc[i+1]['low'])


def merge_adjacent_extremes(extreme_indices, df, min_bars=5):
    """Merge adjacent extreme points with minimum gap"""
    if len(extreme_indices) == 0:
        return []
    
    merged = []
    last_idx = extreme_indices[0]
    
    for i in range(1, len(extreme_indices)):
        current = extreme_indices[i]
        if current - last_idx >= min_bars:
            merged.append(last_idx)
            last_idx = current
    
    merged.append(last_idx)
    return merged


def identify_bi(df, min_bars=5):
    """Identify Bi (笔) - basic price segments"""
    top_indices = []
    bottom_indices = []
    
    for i in range(1, len(df) - 1):
        if is_fenxing(df, i, 'top'):
            top_indices.append(i)
        if is_fenxing(df, i, 'bottom'):
            bottom_indices.append(i)
    
    top_indices = merge_adjacent_extremes(top_indices, df, min_bars)
    bottom_indices = merge_adjacent_extremes(bottom_indices, df, min_bars)
    
    all_points = []
    for idx in top_indices:
        all_points.append({'index': idx, 'date': df.iloc[idx]['date'], 
                          'price': df.iloc[idx]['high'], 'type': 'top'})
    for idx in bottom_indices:
        all_points.append({'index': idx, 'date': df.iloc[idx]['date'], 
                          'price': df.iloc[idx]['low'], 'type': 'bottom'})
    
    all_points.sort(key=lambda x: x['index'])
    
    bi_list = []
    filtered_points = []
    last_type = None
    
    for p in all_points:
        if last_type is None or p['type'] != last_type:
            filtered_points.append(p)
            last_type = p['type']
    
    for i in range(len(filtered_points) - 1):
        p1 = filtered_points[i]
        p2 = filtered_points[i + 1]
        
        if p1['type'] == p2['type']:
            continue
        
        direction = 'up' if p1['type'] == 'bottom' else 'down'
        
        bi_list.append({
            'start_date': p1['date'],
            'start_price': p1['price'],
            'end_date': p2['date'],
            'end_price': p2['price'],
            'high': max(p1['price'], p2['price']),
            'low': min(p1['price'], p2['price']),
            'direction': direction,
            'amplitude': abs(p2['price'] - p1['price']) / p1['price'],
            'start_index': p1['index'],
            'end_index': p2['index']
        })
    
    return pd.DataFrame(bi_list) if bi_list else pd.DataFrame()


def find_zhongshu(bi_df, min_bi_count=3):
    """Identify Zhongshu (中枢)"""
    if bi_df is None or len(bi_df) < min_bi_count:
        return []
    
    zhongshu_list = []
    
    for i in range(len(bi_df) - min_bi_count + 1):
        bis = bi_df.iloc[i:i+min_bi_count]
        
        overlap_high = bis['high'].min()
        overlap_low = bis['low'].max()
        
        if overlap_high > overlap_low:
            zhongshu = {
                'start_date': bis.iloc[0]['start_date'],
                'end_date': bis.iloc[-1]['end_date'],
                'high': overlap_high,
                'low': overlap_low,
                'mid': (overlap_high + overlap_low) / 2,
                'width': overlap_high - overlap_low,
                'bi_count': len(bis),
                'first_bi_direction': bis.iloc[0]['direction']
            }
            
            merged = False
            for z in zhongshu_list:
                if (zhongshu['low'] <= z['high'] + 0.01 and zhongshu['high'] >= z['low'] - 0.01):
                    z['high'] = max(z['high'], zhongshu['high'])
                    z['low'] = min(z['low'], zhongshu['low'])
                    z['mid'] = (z['high'] + z['low']) / 2
                    z['width'] = z['high'] - z['low']
                    z['end_date'] = zhongshu['end_date']
                    z['bi_count'] += 1
                    merged = True
                    break
            
            if not merged:
                zhongshu_list.append(zhongshu)
    
    return zhongshu_list


def find_beichi(bi_df, window=3, threshold=0.8):
    """Identify Beichi (背驰) - divergence"""
    if bi_df is None or len(bi_df) < window * 2:
        return []
    
    beichi_points = []
    
    for i in range(len(bi_df) - window):
        window_bis = bi_df.iloc[i:i+window]
        first_direction = window_bis.iloc[0]['direction']
        
        all_same = all(bi['direction'] == first_direction for _, bi in window_bis.iterrows())
        
        if not all_same:
            continue
        
        powers = [bi['amplitude'] for bi in window_bis.itertuples()]
        
        if powers[-1] < powers[0] * threshold:
            beichi_points.append({
                'index': i + window - 1,
                'date': window_bis.iloc[-1]['end_date'],
                'direction': first_direction,
                'power_ratio': powers[-1] / powers[0] if powers[0] > 0 else 0,
                'signal': 'sell' if first_direction == 'up' else 'buy',
                'bi_index_start': i,
                'bi_index_end': i + window - 1
            })
    
    return beichi_points


def identify_trend(bi_df, zhongshu_list):
    """Identify trend type"""
    if bi_df is None or len(bi_df) < 3:
        return 'unknown', 'neutral'
    
    if len(zhongshu_list) == 0:
        ups = len(bi_df[bi_df['direction'] == 'up'])
        downs = len(bi_df[bi_df['direction'] == 'down'])
        
        if ups > downs * 1.5:
            return 'uptrend', 'bullish'
        elif downs > ups * 1.5:
            return 'downtrend', 'bearish'
        else:
            return 'consolidation', 'neutral'
    
    last_zhongshu = zhongshu_list[-1]
    last_bi = bi_df.iloc[-1]
    
    if last_bi['direction'] == 'up':
        if last_bi['low'] > last_zhongshu['low']:
            return 'uptrend', 'bullish'
        else:
            return 'consolidation', 'neutral'
    else:
        if last_bi['high'] < last_zhongshu['high']:
            return 'downtrend', 'bearish'
        else:
            return 'consolidation', 'neutral'


def generate_signal(bi_df, zhongshu_list, beichi_list, current_price, current_date):
    """Generate trading signals"""
    signals = []
    
    if bi_df is None or len(bi_df) == 0:
        return [{'date': current_date, 'signal': 'watch', 'reason': 'insufficient data', 'confidence': 0}]
    
    last_bi = bi_df.iloc[-1]
    last_direction = last_bi['direction']
    trend, sentiment = identify_trend(bi_df, zhongshu_list)
    
    # Signal priority: Beichi > Zhongshu breakout > Trend
    
    # Beichi signal (highest priority)
    if len(beichi_list) > 0:
        last_beichi = beichi_list[-1]
        signals.append({
            'date': current_date,
            'signal': last_beichi['signal'],
            'signal_type': '背驰信号',
            'reason': f"Beichi: {last_beichi['direction']} power weakened (ratio {last_beichi['power_ratio']:.2f})",
            'confidence': 0.85,
            'priority': 1
        })
    
    # Zhongshu signals
    if len(zhongshu_list) > 0:
        zhongshu = zhongshu_list[-1]
        
        if last_direction == 'up':
            if current_price > zhongshu['high'] * 1.01:  # 1% threshold
                signals.append({
                    'date': current_date,
                    'signal': 'buy',
                    'signal_type': '中枢突破',
                    'reason': f"Breakout above zhongshu {zhongshu['high']:.2f}",
                    'confidence': 0.75,
                    'priority': 2
                })
            elif current_price < zhongshu['low'] * 0.99:
                signals.append({
                    'date': current_date,
                    'signal': 'sell',
                    'signal_type': '中枢跌破',
                    'reason': f"Fell below zhongshu {zhongshu['low']:.2f}",
                    'confidence': 0.75,
                    'priority': 2
                })
        else:
            if current_price < zhongshu['low'] * 0.99:
                signals.append({
                    'date': current_date,
                    'signal': 'sell',
                    'signal_type': '中枢跌破',
                    'reason': f"Fell below zhongshu {zhongshu['low']:.2f}",
                    'confidence': 0.75,
                    'priority': 2
                })
            elif current_price > zhongshu['high'] * 1.01:
                signals.append({
                    'date': current_date,
                    'signal': 'buy',
                    'signal_type': '中枢突破',
                    'reason': f"Breakout above zhongshu {zhongshu['high']:.2f}",
                    'confidence': 0.75,
                    'priority': 2
                })
    
    # Trend signal
    signals.append({
        'date': current_date,
        'signal': 'trend',
        'signal_type': '趋势参考',
        'reason': f"Trend: {trend} | Sentiment: {sentiment}",
        'confidence': 0.6 + (0.1 if sentiment == 'bullish' else 0.1 if sentiment == 'bearish' else 0),
        'priority': 3
    })
    
    # Sort by priority and confidence
    signals.sort(key=lambda x: (x['priority'], -x['confidence']))
    
    return signals


# ============ Multi-Level Analysis ============

LEVELS = {
    '1min': {'min_bars': 3, 'func': lambda ts_code, sd, ed: get_minute_data(ts_code, '1min', sd, ed)},
    '5min': {'min_bars': 3, 'func': lambda ts_code, sd, ed: get_minute_data(ts_code, '5min', sd, ed)},
    '15min': {'min_bars': 3, 'func': lambda ts_code, sd, ed: get_minute_data(ts_code, '15min', sd, ed)},
    '30min': {'min_bars': 3, 'func': lambda ts_code, sd, ed: get_minute_data(ts_code, '30min', sd, ed)},
    '60min': {'min_bars': 3, 'func': lambda ts_code, sd, ed: get_minute_data(ts_code, '60min', sd, ed)},
    'daily': {'min_bars': 5, 'func': lambda ts_code, sd, ed: get_stock_data(ts_code, sd, ed)},
}


def analyze_level(ts_code, level, start_date, end_date):
    """Analyze a specific level"""
    config = LEVELS.get(level, LEVELS['daily'])
    
    if level == 'daily':
        df = config['func'](ts_code, start_date, end_date)
        if df is not None:
            df = df.rename(columns={'trade_date': 'date'}) if 'trade_date' in df.columns else df
    else:
        df = config['func'](ts_code, start_date, end_date)
        if df is not None:
            df = df.rename(columns={'trade_time': 'date'}) if 'trade_time' in df.columns else df
    
    if df is None or df.empty:
        return None
    
    bi_df = identify_bi(df, min_bars=config['min_bars'])
    zhongshu_list = find_zhongshu(bi_df)
    beichi_list = find_beichi(bi_df)
    
    current_price = df.iloc[-1]['close']
    current_date = df.iloc[-1]['date']
    
    trend, sentiment = identify_trend(bi_df, zhongshu_list)
    signals = generate_signal(bi_df, zhongshu_list, beichi_list, current_price, current_date)
    
    return {
        'level': level,
        'df': df,
        'bi_df': bi_df,
        'zhongshu_list': zhongshu_list,
        'beichi_list': beichi_list,
        'trend': trend,
        'sentiment': sentiment,
        'signals': signals,
        'current_price': current_price,
        'current_date': current_date,
        'bi_count': len(bi_df),
        'zhongshu_count': len(zhongshu_list),
        'beichi_count': len(beichi_list)
    }


def multi_level_analysis(ts_code, start_date='20250101', end_date=None, levels=None):
    """Perform multi-level analysis"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    if levels is None:
        levels = ['daily', '60min', '30min', '15min', '5min']
    
    results = {}
    for level in levels:
        result = analyze_level(ts_code, level, start_date, end_date)
        if result:
            results[level] = result
    
    return results


# ============ Visualization ============

def plot_kline_with_chan(df, bi_df, zhongshu_list, beichi_list, title="Chan Theory Analysis", save_path=None):
    """Plot K-line chart with Chan Theory annotations"""
    if df is None or df.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Plot K-line
    for idx, row in df.iterrows():
        color = 'red' if row['close'] >= row['open'] else 'green'
        ax.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=0.5)
        ax.plot([idx, idx], [row['open'], row['close']], color=color, linewidth=1.5)
    
    # Plot Bi
    if bi_df is not None and not bi_df.empty:
        for _, bi in bi_df.iterrows():
            start_idx = bi['start_index']
            end_idx = bi['end_index']
            color = 'r' if bi['direction'] == 'up' else 'g'
            ax.plot([start_idx, end_idx], [bi['start_price'], bi['end_price']], 
                   color=color, linewidth=2, alpha=0.8)
    
    # Plot Zhongshu
    if zhongshu_list:
        for z in zhongshu_list:
            start_idx = df[df['date'] == z['start_date']].index[0] if z['start_date'] in df['date'].values else 0
            end_idx = df[df['date'] == z['end_date']].index[0] if z['end_date'] in df['date'].values else len(df) - 1
            
            rect = Rectangle((start_idx, z['low']), 
                            end_idx - start_idx + 1, 
                            z['high'] - z['low'],
                            linewidth=2, edgecolor='blue', facecolor='blue', alpha=0.2)
            ax.add_patch(rect)
            
            ax.axhline(y=z['mid'], color='blue', linestyle='--', alpha=0.5, linewidth=1)
    
    # Plot Beichi points
    if beichi_list:
        for bc in beichi_list:
            idx = bc['index']
            if idx < len(df):
                ax.scatter(idx, df.iloc[idx]['close'], color='purple', s=100, marker='*', zorder=5)
    
    ax.set_title(title, fontsize=14)
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    
    # Format x-axis
    n = len(df)
    step = max(1, n // 20)
    ax.set_xticks(range(0, n, step))
    ax.set_xticklabels([str(df.iloc[i]['date'])[:10] for i in range(0, n, step)], rotation=45)
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
        return save_path
    
    return fig


def plot_multi_level_summary(results, save_path=None):
    """Plot multi-level analysis summary"""
    if not results:
        return None
    
    fig, axes = plt.subplots(len(results), 1, figsize=(14, 4 * len(results)))
    
    if len(results) == 1:
        axes = [axes]
    
    for ax, (level, result) in zip(axes, results.items()):
        bi_df = result['bi_df']
        if bi_df is None or bi_df.empty:
            continue
        
        # Simple line chart of Bi
        colors = ['red' if d == 'up' else 'green' for d in bi_df['direction']]
        ax.bar(range(len(bi_df)), bi_df['amplitude'] * 100, color=colors, alpha=0.7)
        
        ax.set_title(f"{level.upper()} | Bi: {result['bi_count']} | Zhongshu: {result['zhongshu_count']} | Trend: {result['trend']}")
        ax.set_ylabel('Amplitude %')
        
        if result['signals']:
            main_signal = result['signals'][0]
            signal_color = 'green' if main_signal['signal'] == 'buy' else 'red' if main_signal['signal'] == 'sell' else 'gray'
            ax.annotate(f"{main_signal['signal_type']}: {main_signal['signal']}", 
                       xy=(len(bi_df)-1, bi_df.iloc[-1]['amplitude']*100),
                       fontsize=10, color=signal_color, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
        return save_path
    
    return fig


# ============ Obsidian Sync ============

def generate_obsidian_note(ts_code, stock_name, results, output_dir=None):
    """Generate Obsidian note for the analysis"""
    if output_dir is None:
        output_dir = OBSIDIAN_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}_{ts_code}_缠论分析.md"
    filepath = os.path.join(output_dir, filename)
    
    # Daily result for main summary
    daily = results.get('daily', {})
    current_price = daily.get('current_price', 0)
    trend = daily.get('trend', 'unknown')
    sentiment = daily.get('sentiment', 'neutral')
    signals = daily.get('signals', [])
    
    # Build content
    content = f"""# {stock_name} ({ts_code}) - 缠论分析

> 分析日期: {date_str}
> 分析级别: 日线、60分钟、30分钟、15分钟、5分钟

---

## 概要

| 指标 | 数值 |
|------|------|
| 当前价格 | {current_price:.2f} |
| 趋势 | {trend} |
| 市场情绪 | {sentiment} |
| 日线笔数 | {daily.get('bi_count', 0)} |
| 日线中枢 | {daily.get('zhongshu_count', 0)} |
| 日线背驰 | {daily.get('beichi_count', 0)} |

---

## 操作信号

"""
    
    for sig in signals:
        sig_icon = "🟢" if sig['signal'] == 'buy' else "🔴" if sig['signal'] == 'sell' else "🟡"
        content += f"- {sig_icon} **{sig['signal_type']}**: {sig['reason']} (置信度: {sig['confidence']:.0%})\n"
    
    # Latest Zhongshu
    zhongshu_list = daily.get('zhongshu_list', [])
    if zhongshu_list:
        z = zhongshu_list[-1]
        content += f"""
---

## 最新中枢

| 属性 | 数值 |
|------|------|
| 区间 | {z['low']:.2f} - {z['high']:.2f} |
| 中位 | {z['mid']:.2f} |
| 宽度 | {z['width']:.2f} |
| 笔数 | {z['bi_count']} |

"""
    
    # Latest Bi
    bi_df = daily.get('bi_df')
    if bi_df is not None and not bi_df.empty:
        last_bi = bi_df.iloc[-1]
        content += f"""---

## 最新笔

| 属性 | 数值 |
|------|------|
| 方向 | {'上涨' if last_bi['direction'] == 'up' else '下跌'} |
| 起始价格 | {last_bi['start_price']:.2f} |
| 结束价格 | {last_bi['end_price']:.2f} |
| 幅度 | {last_bi['amplitude']*100:.2f}% |

"""
    
    # Multi-level summary
    content += """---

## 多级别分析

| 级别 | 笔数 | 中枢 | 背驰 | 趋势 |
|------|------|------|------|------|
"""
    
    for level in ['daily', '60min', '30min', '15min', '5min']:
        if level in results:
            r = results[level]
            content += f"| {level} | {r['bi_count']} | {r['zhongshu_count']} | {r['beichi_count']} | {r['trend']} |\n"
    
    # Signals by level
    content += """
---

## 各级别信号

"""
    
    for level in ['daily', '60min', '30min', '15min', '5min']:
        if level in results and results[level]['signals']:
            r = results[level]
            sig = r['signals'][0]
            sig_icon = "🟢" if sig['signal'] == 'buy' else "🔴" if sig['signal'] == 'sell' else "🟡"
            content += f"- **{level.upper()}**: {sig_icon} {sig['signal_type']} - {sig['reason']}\n"
    
    # Tags
    content += f"""
---

标签: #缠论 #股票分析 #{stock_name} #缠论_{ts_code.split('.')[0]}

---
*由小智自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def generate_index_note(results_dir=None, output_dir=None):
    """Generate index note for all analyses"""
    if output_dir is None:
        output_dir = OBSIDIAN_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}_缠论分析索引.md"
    filepath = os.path.join(output_dir, filename)
    
    # Find all analysis files
    files = []
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            if f.endswith('_缠论分析.md'):
                files.append(f)
    
    files.sort(reverse=True)
    
    content = f"""# 缠论分析索引

> 更新日期: {date_str}
> 总计: {len(files)} 篇分析

---

## 最近分析

"""
    
    for f in files[:20]:
        content += f"- [[{f.replace('.md', '')}]]\n"
    
    if len(files) > 20:
        content += f"\n... 共 {len(files)} 篇\n"
    
    content += """
---

标签: #缠论 #股票分析 #索引
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


# ============ Main Analysis ============

def chan_analysis(ts_code, start_date='20250101', end_date=None, levels=None, sync_obsidian=True):
    """Main Chan Theory analysis function"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    if levels is None:
        levels = ['daily', '60min', '30min', '15min', '5min']
    
    # Get stock info
    basic = get_stock_basic(ts_code)
    stock_name = basic.get('name', ts_code) if basic else ts_code
    
    print(f"[DATA] Fetching data for {stock_name} ({ts_code})...")
    
    # Multi-level analysis
    print(f"[LEVEL] Starting multi-level analysis...")
    results = multi_level_analysis(ts_code, start_date, end_date, levels)
    
    if not results:
        print(f"[ERROR] No data retrieved")
        return None
    
    print(f"[OK] Multi-level analysis complete: {', '.join(results.keys())}")
    
    # Generate plots
    print(f"[PLOT] Generating visualizations...")
    plots = {}
    
    # Daily chart
    if 'daily' in results:
        daily = results['daily']
        save_path = os.path.join(PLOT_DIR, f"{ts_code}_daily.png")
        plot_path = plot_kline_with_chan(
            daily['df'], daily['bi_df'], daily['zhongshu_list'], 
            daily['beichi_list'], f"{stock_name} 日线缠论分析", save_path
        )
        if plot_path:
            plots['daily'] = plot_path
    
    # Multi-level summary
    summary_path = os.path.join(PLOT_DIR, f"{ts_code}_multi_level.png")
    plot_multi_level_summary(results, summary_path)
    plots['summary'] = summary_path
    
    print(f"[OK] Plots saved to {PLOT_DIR}")
    
    # Sync to Obsidian
    if sync_obsidian:
        print(f"[SYNC] Syncing to Obsidian...")
        note_path = generate_obsidian_note(ts_code, stock_name, results)
        index_path = generate_index_note()
        print(f"[OK] Obsidian notes saved")
        print(f"     - {note_path}")
        print(f"     - {index_path}")
    
    # Build summary
    summary = {
        'stock_name': stock_name,
        'ts_code': ts_code,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'levels_analyzed': list(results.keys()),
        'plots': plots,
        'results': {k: {
            'trend': v['trend'],
            'sentiment': v['sentiment'],
            'bi_count': v['bi_count'],
            'zhongshu_count': v['zhongshu_count'],
            'beichi_count': v['beichi_count'],
            'current_price': v['current_price'],
            'signals': v['signals']
        } for k, v in results.items()}
    }
    
    return summary


def print_analysis_summary(summary):
    """Print analysis summary"""
    if summary is None:
        print("[ERROR] Analysis failed")
        return
    
    print("\n" + "="*70)
    print(f"[REPORT] Chan Theory Analysis: {summary['stock_name']} ({summary['ts_code']})")
    print("="*70)
    print(f"[DATE] {summary['analysis_date']}")
    print(f"[LEVELS] {', '.join(summary['levels_analyzed'])}")
    
    print("\n[MULTI-LEVEL SUMMARY]")
    print("-"*70)
    print(f"{'Level':<10} {'Bi':<6} {'ZS':<6} {'BC':<6} {'Trend':<15} {'Signal'}")
    print("-"*70)
    
    for level in ['daily', '60min', '30min', '15min', '5min']:
        if level in summary['results']:
            r = summary['results'][level]
            signal = r['signals'][0]['signal'] if r['signals'] else '-'
            print(f"{level:<10} {r['bi_count']:<6} {r['zhongshu_count']:<6} {r['beichi_count']:<6} {r['trend']:<15} {signal}")
    
    print("\n[PLOTS]")
    for name, path in summary['plots'].items():
        print(f"  - {name}: {path}")
    
    print("\n" + "="*70)


def json_serializer(obj):
    """JSON serializer for non-standard objects"""
    if isinstance(obj, (pd.Timestamp, pd.Timedelta, datetime)):
        return str(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def save_analysis_json(summary, output_path=None):
    """Save analysis summary to JSON"""
    if summary is None:
        return
    
    if output_path is None:
        output_path = os.path.join(CHAN_DIR, f"{summary['ts_code']}_analysis_v2.json")
    
    # Remove non-serializable parts
    output = {k: v for k, v in summary.items() if k != 'plots'}
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=json_serializer)
    
    print(f"[SAVE] Analysis saved: {output_path}")


# ============ Main ============

if __name__ == "__main__":
    import sys
    
    print("""
    =======================================================
         Chan Theory Stock Analysis v2.0
         - Multi-Level Analysis
         - Visualization
         - Obsidian Sync
    =======================================================
    """)
    
    ts_code = '000001.SZ'
    start_date = '20250101'
    levels = ['daily', '60min', '30min']
    
    if len(sys.argv) > 1:
        ts_code = sys.argv[1]
    if len(sys.argv) > 2:
        start_date = sys.argv[2]
    if len(sys.argv) > 3:
        levels = sys.argv[3].split(',')
    
    summary = chan_analysis(ts_code, start_date=start_date, levels=levels)
    print_analysis_summary(summary)
    save_analysis_json(summary)
