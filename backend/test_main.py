# test_main.py
import pytest
from fastapi.testclient import TestClient
from main import app # Mengimpor aplikasi FastAPI Anda dari main.py
import pandas as pd # Import pandas

# Membuat instance TestClient
client = TestClient(app)

# --- Fungsi Mock untuk fetch_yfinance_data ---
# Anda bisa membuat variasi dari fungsi mock ini sesuai kebutuhan tes

def mock_fetch_success_data(tickers: list):
    """Mock untuk fetch_yfinance_data yang mengembalikan data sukses."""
    print(">>> MOCK FETCH SUCCESS DATA DIPANGGIL <<<")
    # Data ini dirancang agar setidaknya beberapa saham lolos filter fundamental
    # dan preferensi di test_create_recommendation_success
    mock_df_fundamentals = pd.DataFrame({
        'company_name': ['Bank A', 'Bank B', 'Tekno C', 'Konsumsi D'], 
        'sector': ['Perbankan', 'Perbankan', 'Teknologi', 'Konsumsi Primer'],
        'is_syariah': [False, True, False, True], 
        'marketCap': [6e12, 8e12, 7e12, 5.5e12], # > 5T
        'pe_ratio': [15, 12, 20, 18],          # >0 dan <30
        'roe': [0.15, 0.18, 0.12, 0.10],       # >0.08
        'der': [1.1, 1.3, 0.5, 1.8]            # <2.0
    }, index=['BKA.JK', 'BKB.JK', 'TKC.JK', 'KSD.JK'])
    
    mock_df_prices = pd.DataFrame({
        'BKA.JK': [1000, 1010, 1020, 1030, 1040] * 51, # Minimal 252 data poin
        'BKB.JK': [2000, 2010, 1990, 2005, 2015] * 51,
        'TKC.JK': [500, 505, 510, 515, 520] * 51,
        'KSD.JK': [3000, 3010, 3000, 2990, 3005] * 51,
    }, index=pd.date_range(start='2023-01-01', periods=255, freq='B')) # Pastikan cukup data
    
    return mock_df_fundamentals, mock_df_prices

def mock_fetch_no_fundamental_match_data(tickers: list):
    """Mock yang mengembalikan data yang tidak akan lolos filter fundamental."""
    print(">>> MOCK FETCH NO FUNDAMENTAL MATCH DATA DIPANGGIL <<<")
    mock_df_fundamentals = pd.DataFrame({ # Semua saham ini akan gagal filter fundamental
        'company_name': ['BadBank E', 'RiskyF F'], 'sector': ['Perbankan', 'Teknologi'],
        'is_syariah': [False, False], 'marketCap': [1e12, 2e12], # Terlalu kecil atau gagal kriteria lain
        'pe_ratio': [50, 35], 'roe': [0.01, 0.02], 'der': [3.0, 2.5]
    }, index=['BBE.JK', 'RKF.JK'])
    
    mock_df_prices = pd.DataFrame({
        'BBE.JK': [100, 101, 102] * 85,
        'RKF.JK': [200, 201, 199] * 85,
    }, index=pd.date_range(start='2023-01-01', periods=255, freq='B'))
    return mock_df_fundamentals, mock_df_prices

# --- Test Cases ---

def test_create_recommendation_success(monkeypatch):
    """Menguji skenario sukses menggunakan mock data."""
    # Gantikan fetch_yfinance_data yang asli dengan mock_fetch_success_data
    monkeypatch.setattr("main.fetch_yfinance_data", mock_fetch_success_data)
    
    test_payload = {
        "initial_capital": 50000000,
        "investment_goal": "Mengembangkan Kekayaan",
        "time_horizon": "Antara 8 - 15 tahun", # -> Long
        "risk_answers": {"q1": "C", "q2": "B", "q3": "A"}, # Risk score: 30+15+20 = 65 (Growth)
        "preferences": {
            "sectors": ["Perbankan"], # Seharusnya BKA.JK dan BKB.JK lolos
            "principles": []
        }
    }
    response = client.post("/api/v1/recommendations", json=test_payload)

    assert response.status_code == 200, f"Gagal! Response: {response.json()}"
    data = response.json()
    assert "analysis_summary" in data
    assert "portfolio_recommendation" in data
    assert "determined_strategy" in data["analysis_summary"]
    assert data["analysis_summary"]["determined_strategy"] == "Growth"
    assert len(data["portfolio_recommendation"]["allocation_details"]) > 0 # Pastikan ada alokasi

def test_create_recommendation_no_stocks_due_to_preferences_error(monkeypatch):
    """
    Menguji skenario di mana preferensi pengguna sangat spesifik sehingga
    tidak ada saham yang lolos filter (setelah data mock berhasil diambil).
    """
    # Gunakan mock data yang sukses, tetapi payload akan menyebabkan kegagalan
    monkeypatch.setattr("main.fetch_yfinance_data", mock_fetch_success_data)
    
    test_payload = {
        "initial_capital": 50000000,
        "investment_goal": "Mengembangkan Kekayaan",
        "time_horizon": "Antara 8 - 15 tahun",
        "risk_answers": {"q1": "C", "q2": "B", "q3": "A"},
        "preferences": {
            "sectors": ["Sektor Fiktif Yang Pasti Tidak Ada"], # Ini akan menyebabkan tidak ada saham lolos
            "principles": []
        }
    }
    response = client.post("/api/v1/recommendations", json=test_payload)

    assert response.status_code == 400, f"Gagal! Response: {response.json()}"
    data = response.json()
    assert "detail" in data
    assert "Tidak cukup saham" in data["detail"]

def test_create_recommendation_no_stocks_due_to_bad_fundamentals_error(monkeypatch):
    """
    Menguji skenario di mana SEMUA saham dari mock data tidak lolos filter fundamental.
    """
    # Gunakan mock data yang berisi saham-saham "buruk"
    monkeypatch.setattr("main.fetch_yfinance_data", mock_fetch_no_fundamental_match_data)
    
    test_payload = {
        "initial_capital": 50000000,
        "investment_goal": "Mengembangkan Kekayaan",
        "time_horizon": "Antara 8 - 15 tahun",
        "risk_answers": {"q1": "C", "q2": "B", "q3": "A"},
        "preferences": { 
            "sectors": [], # Semua sektor
            "principles": []
        }
    }
    response = client.post("/api/v1/recommendations", json=test_payload)

    assert response.status_code == 400, f"Gagal! Response: {response.json()}"
    data = response.json()
    assert "detail" in data
    # Pesan error ini berasal dari `generate_optimal_portfolio` ketika `quality_tickers_df` kosong
    assert "Tidak ada saham yang lolos filter fundamental awal" in data["detail"] or \
           "Tidak cukup saham yang lolos filter (minimal 2)" in data["detail"]


# Di dalam file test_main.py

def test_recommendation_with_original_mock_data(monkeypatch):
    """Menguji endpoint dengan data mock yang lebih sederhana (seperti yang Anda buat)."""

    def mock_fetch_simple_data(tickers: list):
        print(">>> MOCK FETCH SIMPLE DATA DIPANGGIL <<<")
        mock_df_fundamentals = pd.DataFrame({
            'company_name': ['Bank A', 'Bank B'], 'sector': ['Perbankan', 'Perbankan'],
            'is_syariah': [False, True], 'marketCap': [6e12, 8e12],
            'pe_ratio': [15, 12], 'roe': [0.15, 0.18], 'der': [1.1, 1.3]
        }, index=['BKA.JK', 'BKB.JK'])
        
        mock_df_prices = pd.DataFrame({
            'BKA.JK': [1000, 1010, 1020, 1030, 1040] * 51,
            'BKB.JK': [2000, 2010, 1990, 2005, 2015] * 51
        }, index=pd.date_range(start='2023-01-01', periods=255, freq='B'))
        return mock_df_fundamentals, mock_df_prices

    monkeypatch.setattr("main.fetch_yfinance_data", mock_fetch_simple_data)
    
    test_payload = {
        "initial_capital": 10000000,
        "investment_goal": "Balanced",
        "time_horizon": "Antara 3 - 7 tahun", # Medium
        "risk_answers": {"q1": "C", "q2": "A", "q3": "B"}, # Risk: 30+5+10 = 45 (Balanced)
        "preferences": {"sectors": [], "principles": []}
    }
    
    response = client.post("/api/v1/recommendations", json=test_payload)
    
    assert response.status_code == 200, f"Gagal! Response: {response.json()}"
    data = response.json()
    assert "portfolio_recommendation" in data
    assert "allocation_details" in data["portfolio_recommendation"]
    
    # --- PERUBAHAN DI SINI ---
    allocation_list = data["portfolio_recommendation"]["allocation_details"]
    # Ambil semua ticker dari list of dictionaries
    allocated_tickers = [item['ticker'] for item in allocation_list] 
    
    assert "BKA.JK" in allocated_tickers
    assert "BKB.JK" in allocated_tickers
    # --- AKHIR PERUBAHAN ---

    assert data["analysis_summary"]["determined_strategy"] == "Balanced"