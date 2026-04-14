"""
Chan Analysis CLI v2.0

用法:
    py chan_cli.py                    # 分析平安银行 (日线+60min+30min)
    py chan_cli.py 000001.SZ         # 分析指定股票
    py chan_cli.py 000001.SZ 20250101 # 指定开始日期
    py chan_cli.py 000001.SZ 20250101 daily,60min,30min,15min,5min  # 指定级别
"""

from chan_theory import chan_analysis, print_analysis_summary, save_analysis_json
import sys

if __name__ == "__main__":
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
