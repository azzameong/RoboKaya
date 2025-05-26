# main.py

# --- 1. Imports ---
import uvicorn
import json
import pandas as pd
import numpy as np
import yfinance as yf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timedelta

from pypfopt import EfficientFrontier, risk_models, expected_returns

# --- 2. Pydantic Models (Definisi Input API) ---
class RiskAnswers(BaseModel):
    q1: str
    q2: str
    q3: str

class Preferences(BaseModel):
    sectors: List[str]
    principles: List[str]

class PortfolioRequest(BaseModel):
    initial_capital: float
    investment_goal: str
    time_horizon: str
    risk_answers: RiskAnswers
    preferences: Preferences

# --- 3. Konstanta dan Helper ---
# Dalam aplikasi nyata, ini bisa diambil dari file konfigurasi atau database
SYARIAH_MAPPING = {
    'BBCA.JK': False, 'BMRI.JK': True, 'TLKM.JK': False, 'ASII.JK': False,
    'UNVR.JK': True, 'GOTO.JK': False, 'ARTO.JK': False, 'MDKA.JK': True,
    'ICBP.JK': True, 'BBNI.JK': False, 'BRIS.JK': True, 'ANTM.JK': True,
    'PGAS.JK': True, 'ADRO.JK': True, 'KLBF.JK': False, 'ACES.JK': True,
    'INDF.JK': True, 'PTBA.JK': True, 'CPIN.JK': True, 'EXCL.JK': True
}
# Untuk pengujian, Anda bisa memulai dengan daftar ticker yang lebih sedikit
# TICKERS_TO_ANALYZE = ['BBCA.JK', 'BMRI.JK', 'TLKM.JK', 'ASII.JK', 'UNVR.JK']
TICKERS_TO_ANALYZE = list(SYARIAH_MAPPING.keys())


# --- 4. Fungsi Inti ---
def fetch_yfinance_data(tickers: list):
    """Menarik data fundamental dan harga historis dari Yahoo Finance."""
    print("--- Memulai Penarikan Data Pasar ---")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2 * 365 + 60) # 2 tahun + buffer
    
    print(f"[INFO] Menarik data harga untuk {len(tickers)} saham dari {start_date.strftime('%Y-%m-%d')} hingga {end_date.strftime('%Y-%m-%d')}...")
    df_prices_raw = yf.download(tickers, start=start_date, end=end_date, interval="1d", progress=False)
    
    if df_prices_raw.empty:
        print("[ERROR] Gagal mengunduh data harga awal. DataFrame mentah kosong.")
        return None, None

    df_prices = df_prices_raw.get('Close')
    if df_prices is None or df_prices.empty:
        print("[ERROR] Kolom 'Close' tidak ditemukan atau DataFrame harga kosong setelah memilih 'Close'.")
        return None, None
    
    # Jika hanya satu ticker, yf.download mungkin mengembalikan Series, ubah ke DataFrame
    if isinstance(df_prices, pd.Series):
        df_prices = df_prices.to_frame(name=tickers[0] if len(tickers) == 1 else 'PRICE_DATA')

    df_prices = df_prices.copy() 

    print(f"[INFO] Data harga mentah diunduh untuk {len(df_prices.columns)} saham.")
    df_prices.dropna(axis=1, how='all', inplace=True) 
    df_prices = df_prices.loc[:, df_prices.isnull().mean() < 0.1]
    
    if df_prices.empty:
        print("[ERROR] Tidak ada saham dengan data harga yang cukup setelah cleaning awal.")
        return None, None
    print(f"[INFO] Jumlah saham dengan data harga valid setelah cleaning awal: {len(df_prices.columns)}")

    print(f"[INFO] Menarik data fundamental untuk {len(df_prices.columns)} saham yang memiliki harga valid...")
    fundamentals_list = []
    valid_tickers_for_fundamentals = df_prices.columns.tolist()

    for ticker_str in valid_tickers_for_fundamentals:
        try:
            print(f"  [DEBUG] Memproses fundamental untuk: {ticker_str}")
            stock_info = yf.Ticker(str(ticker_str)).info
            market_cap = stock_info.get('marketCap')
            
            if market_cap is None or market_cap == 0:
                print(f"  [WARN] Data market cap tidak ada atau 0 untuk {ticker_str}. Saham ini dilewati.")
                continue

            fundamentals = {
                'ticker': str(ticker_str), 'company_name': stock_info.get('shortName', str(ticker_str)),
                'sector': stock_info.get('sector', 'N/A'), 'is_syariah': SYARIAH_MAPPING.get(str(ticker_str), False),
                'marketCap': market_cap, 'pe_ratio': stock_info.get('trailingPE'),
                'roe': stock_info.get('returnOnEquity'), 'der': stock_info.get('debtToEquity')
            }
            fundamentals_list.append(fundamentals)
        except Exception as e:
            print(f"  [WARN] Gagal menarik data fundamental untuk {ticker_str}: {e}. Saham ini dilewati.")
            continue
    
    if not fundamentals_list:
        print("[ERROR] Tidak ada data fundamental yang berhasil ditarik untuk saham manapun.")
        return None, None
    print(f"[INFO] Jumlah saham dengan data fundamental berhasil ditarik: {len(fundamentals_list)}")

    df_fundamentals = pd.DataFrame(fundamentals_list).set_index('ticker')
    
    # Sinkronisasi akhir: pastikan kedua DataFrame memiliki ticker yang sama
    common_tickers = df_prices.columns.intersection(df_fundamentals.index)
    df_prices = df_prices[common_tickers]
    df_fundamentals = df_fundamentals.loc[common_tickers]
    
    df_prices.dropna(axis=0, how='any', inplace=True) # Hapus baris tanggal jika ada NaN

    if df_prices.empty or df_fundamentals.empty or len(df_prices.columns) < 2:
        print("[ERROR] Data harga atau fundamental menjadi kosong atau kurang dari 2 saham setelah sinkronisasi akhir.")
        return None, None

    print(f"[INFO] Jumlah saham final setelah sinkronisasi: {len(df_prices.columns)}")
    print("--- Penarikan Data Selesai ---")
    return df_fundamentals, df_prices

def analyze_user_input(request: PortfolioRequest) -> dict:
    """Menganalisis input dari borang dan mengubahnya menjadi parameter teknis."""
    print("[INFO] Menganalisis input pengguna...")
    
    risk_score_map = {'q1': {'A': 10, 'B': 20, 'C': 30, 'D': 40},
                      'q2': {'A': 5, 'B': 15, 'C': 25},
                      'q3': {'A': 20, 'B': 10, 'C': 25}}
    risk_score = (risk_score_map['q1'].get(request.risk_answers.q1, 10) +
                  risk_score_map['q2'].get(request.risk_answers.q2, 5) +
                  risk_score_map['q3'].get(request.risk_answers.q3, 10))

    time_horizon_map = {"Kurang dari 3 tahun": 'Short', "Antara 3 - 7 tahun": 'Medium',
                        "Antara 8 - 15 tahun": 'Long', "Lebih dari 15 tahun": 'VeryLong'}
    time_horizon_category = time_horizon_map.get(request.time_horizon, 'Medium')

    strategy = 'Balanced'
    if time_horizon_category in ['Long', 'VeryLong']:
        if risk_score > 70: strategy = 'Aggressive Growth'
        elif risk_score > 40: strategy = 'Growth'
        else: strategy = 'Balanced Growth'
    elif time_horizon_category == 'Medium':
        if risk_score > 70: strategy = 'Balanced Growth'
        elif risk_score > 40: strategy = 'Balanced'
        else: strategy = 'Income'
    else: # Short
        if risk_score > 40: strategy = 'Income'
        else: strategy = 'Capital Preservation'

    constraints_map = {
        'Capital Preservation': {"optimization_target": "min_volatility"},
        'Income': {"optimization_target": "max_sharpe"},
        'Balanced': {"optimization_target": "max_sharpe"},
        'Balanced Growth': {"optimization_target": "max_sharpe"},
        'Growth': {"optimization_target": "max_sharpe"},
        'Aggressive Growth': {"optimization_target": "max_sharpe"}
    }
    technical_constraints = constraints_map.get(strategy)

    stock_universe_filters = {
        "sectors": request.preferences.sectors,
        "syariah_only": "Syariah" in request.preferences.principles,
        "esg_focus": "ESG" in request.preferences.principles
    }
    
    return {
        "risk_score": risk_score, "investment_strategy": strategy,
        "technical_constraints": technical_constraints,
        "stock_universe_filters": stock_universe_filters
    }

def generate_optimal_portfolio(initial_capital: float, user_preferences: dict, technical_constraints: dict, df_fundamentals: pd.DataFrame, df_prices: pd.DataFrame):
    """Menghasilkan rekomendasi portofolio optimal."""
    print("[INFO] Memulai proses optimisasi portofolio...")
    df_processed = df_fundamentals.copy()
    # Menggunakan kolom baru untuk menghindari SettingWithCopyWarning pada DataFrame slice
    df_processed['der_processed'] = df_processed['der'].fillna(0) 
    df_processed['pe_ratio_processed'] = df_processed['pe_ratio'].fillna(999) 
    df_processed['roe_processed'] = df_processed['roe'].fillna(-1)
    
    fundamental_filter = (
        (df_processed['marketCap'] > 5e12) & 
        (df_processed['pe_ratio_processed'] > 0) & 
        (df_processed['pe_ratio_processed'] < 30) & 
        (df_processed['roe_processed'] > 0.08) &
        (df_processed['der_processed'] < 2.0)
    )
    quality_tickers_df = df_processed[fundamental_filter]
    print(f"[DEBUG] Jumlah saham lolos filter fundamental awal: {len(quality_tickers_df)}")
    
    if quality_tickers_df.empty:
        return {"error": "Tidak ada saham yang lolos filter fundamental awal."}
    
    # Filter Preferensi Pengguna
    if user_preferences.get('syariah_only', False):
        quality_tickers_df = quality_tickers_df[quality_tickers_df['is_syariah'] == True]
    print(f"[DEBUG] Jumlah saham setelah filter syariah (jika ada): {len(quality_tickers_df)}")
    
    selected_sectors = user_preferences.get('sectors', [])
    if selected_sectors: # Hanya filter jika ada sektor yang dipilih
        quality_tickers_df = quality_tickers_df[quality_tickers_df['sector'].isin(selected_sectors)]
    print(f"[DEBUG] Jumlah saham setelah filter sektor (jika ada): {len(quality_tickers_df)}")
    
    # Sinkronisasi ticker yang lolos filter dengan data harga yang tersedia
    final_eligible_tickers = [t for t in quality_tickers_df.index.tolist() if t in df_prices.columns]
    print(f"[DEBUG] Jumlah saham di final_eligible_tickers (setelah sinkronisasi dgn df_prices): {len(final_eligible_tickers)}")
    
    if len(final_eligible_tickers) < 2:
        return {"error": "Tidak cukup saham yang lolos filter (minimal 2) untuk membuat portofolio yang terdiversifikasi."}
    
    print(f"[INFO] Saham yang lolos semua filter: {final_eligible_tickers}")
    df_prices_filtered = df_prices[final_eligible_tickers].copy()
    
    # Pemeriksaan akhir pada data harga
    if df_prices_filtered.isnull().values.any():
        print("[WARN] Ada nilai NaN di data harga setelah filter, akan di-dropna (baris).")
        df_prices_filtered.dropna(axis=0, how='any', inplace=True)
        if df_prices_filtered.empty or len(df_prices_filtered) < 60: # Minimal 60 hari data untuk PyPortfolioOpt
            return {"error": "Tidak cukup data harga historis setelah menghapus NaN (minimal 60 hari)."}
    
    try:
        mu = expected_returns.capm_return(df_prices_filtered)
        S = risk_models.CovarianceShrinkage(df_prices_filtered).ledoit_wolf()
        ef = EfficientFrontier(mu, S)
        
        optimization_target = technical_constraints.get("optimization_target", "max_sharpe")
        if optimization_target == "min_volatility":
            weights = ef.min_volatility()
        else:
            weights = ef.max_sharpe()
            
        cleaned_weights = ef.clean_weights()
        expected_return, annual_volatility, sharpe_ratio = ef.portfolio_performance(verbose=False)
    except Exception as e:
        print(f"[ERROR] Exception saat optimisasi: {e}")
        return {"error": f"Optimisasi portofolio gagal: {e}"}
    
    allocation_details = []
    total_invested_actually = 0
    for ticker, weight in cleaned_weights.items():
        if weight > 0 and ticker in df_prices_filtered.columns:
            last_price = df_prices_filtered[ticker].iloc[-1]
            if pd.isna(last_price) or last_price <= 0:
                print(f"[WARN] Harga terakhir tidak valid untuk {ticker}. Melewatkan alokasi.")
                continue
                
            number_of_lots = np.floor((initial_capital * weight) / (100 * last_price))
            actual_invested = number_of_lots * 100 * last_price
            if number_of_lots > 0:
                total_invested_actually += actual_invested
                # Ambil company_name dari df_fundamentals (bukan df_processed) karena df_processed mungkin tidak berisi semua kolom asli
                company_name_original = df_fundamentals.loc[ticker, 'company_name'] if ticker in df_fundamentals.index else 'N/A'
                sector_original = df_fundamentals.loc[ticker, 'sector'] if ticker in df_fundamentals.index else 'N/A'

                allocation_details.append({
                    "ticker": ticker, 
                    "company_name": company_name_original,
                    "sector": sector_original,
                    "target_weight_percentage": f"{weight:.2%}",
                    "invested_capital": f"Rp {actual_invested:,.0f}",
                    "lots": int(number_of_lots),
                    "price_per_share": f"Rp {last_price:,.0f}"
                })
    
    for item in allocation_details:
        invested_val = float(item['invested_capital'].replace('Rp ', '').replace(',', ''))
        if total_invested_actually > 0:
            item['actual_weight_percentage'] = f"{(invested_val / total_invested_actually):.2%}"
        else:
            item['actual_weight_percentage'] = "0.00%"

    unallocated_cash = initial_capital - total_invested_actually
    last_data_date_str = "N/A"
    if not df_prices_filtered.empty:
        last_data_date_str = df_prices_filtered.index[-1].strftime('%Y-%m-%d')

    return {
        "portfolio_name": "Portofolio Optimal Ronbokaya (Live Data)",
        "data_as_of_date": last_data_date_str,
        "portfolio_metrics": {
            "expected_annual_return": f"{expected_return:.2%}", 
            "annual_volatility_risk": f"{annual_volatility:.2%}", 
            "sharpe_ratio": f"{sharpe_ratio:.2f}"
        },
        "allocation_details": allocation_details,
        "financial_summary": {
            "total_capital_invested": f"Rp {total_invested_actually:,.0f}",
            "unallocated_cash_due_to_lot_rounding": f"Rp {unallocated_cash:,.0f}",
            "percentage_of_capital_invested": f"{(total_invested_actually / initial_capital):.2%}" if initial_capital > 0 else "N/A"
        }
    }

# --- 5. Inisiasi Aplikasi FastAPI & Endpoint ---
app = FastAPI(
    title="Ronbokaya API",
    description="API untuk memberikan rekomendasi portofolio investasi yang dipersonalisasi.",
    version="1.0.0"
)

@app.post("/api/v1/recommendations", summary="Membuat Rekomendasi Portofolio")
async def create_recommendation(request: PortfolioRequest):
    try:
        print(f"[INFO] Menerima request: {request.model_dump_json(indent=2)}")
        analyzed_params = analyze_user_input(request)
        print(f"[INFO] Parameter hasil analisis: {json.dumps(analyzed_params, indent=2)}")
        
        df_fundamentals, df_prices = fetch_yfinance_data(TICKERS_TO_ANALYZE)
        
        if df_fundamentals is None or df_prices is None or df_fundamentals.empty or df_prices.empty:
            print("[ERROR] Gagal mengambil data pasar yang valid dari fetch_yfinance_data di endpoint.")
            raise HTTPException(status_code=503, detail="Gagal mengambil data pasar saat ini. Coba lagi beberapa saat.")

        portfolio_result = generate_optimal_portfolio(
            initial_capital=request.initial_capital,
            user_preferences=analyzed_params["stock_universe_filters"],
            technical_constraints=analyzed_params["technical_constraints"],
            df_fundamentals=df_fundamentals,
            df_prices=df_prices
        )

        if "error" in portfolio_result:
            print(f"[ERROR] Error dari generate_optimal_portfolio: {portfolio_result['error']}")
            raise HTTPException(status_code=400, detail=portfolio_result["error"])
        
        final_response = {
            "input_summary": {
                "initial_capital": f"Rp {request.initial_capital:,.0f}",
                "investment_goal": request.investment_goal,
                "time_horizon": request.time_horizon,
                "risk_score": analyzed_params['risk_score'],
                "determined_strategy": analyzed_params['investment_strategy']
            },
            "portfolio_recommendation": portfolio_result
        }
        print("[INFO] Rekomendasi berhasil dibuat.")
        return final_response

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"[FATAL] Terjadi kesalahan tidak terduga di endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan internal di server: {str(e)}")

# --- 6. Cara Menjalankan Server ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)