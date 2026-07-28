"""🚀 AI Trading Brain — Flask API Backend"""
import os
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

from brain.evolving_brain import EvolvingBrain
from brain.market_pipeline import scan_market, ASSETS

app = Flask(__name__)
CORS(app)

# Initialize brain
brain = EvolvingBrain()

# Portfolio state
portfolio = {
    "cash": 10000.0,
    "positions": [],
    "trades": [],
    "total_pnl": 0.0,
    "wins": 0,
    "losses": 0,
    "max_value": 10000.0,
    "min_value": 10000.0
}

# Load portfolio from disk
PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), 'data', 'portfolio.json')
os.makedirs(os.path.dirname(PORTFOLIO_PATH), exist_ok=True)

def save_portfolio():
    with open(PORTFOLIO_PATH, 'w') as f:
        json.dump(portfolio, f, indent=2, default=str)

def load_portfolio():
    global portfolio
    if os.path.exists(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH) as f:
            loaded = json.load(f)
            portfolio.update(loaded)

load_portfolio()

# Auto-evolution thread (every 10 min)
def evolution_loop():
    while True:
        time.sleep(600)
        try:
            brain.evolve()
        except Exception:
            pass

threading.Thread(target=evolution_loop, daemon=True).start()


@app.route('/')
def index():
    return jsonify({
        "name": "AI Trading Brain API",
        "version": "2.0.0",
        "status": "running",
        "brain": brain.get_health(),
        "endpoints": [
            "GET /api/health",
            "GET /api/market/scan",
            "POST /api/trade",
            "GET /api/portfolio",
            "POST /api/portfolio/reset",
            "POST /api/brain/evolve",
            "GET /api/brain/health"
        ]
    })


@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy",
        "platform": "AI Trading Brain v2.0.0",
        "runtime": "Python/Flask",
        "brain_neurons": brain.NUM_NEURONS,
        "brain_generation": brain.generation,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/market/scan')
def market_scan():
    data = scan_market(brain)
    return jsonify(data)


@app.route('/api/portfolio')
def get_portfolio():
    # Calculate current holdings value
    prices = {}
    try:
        from brain.market_pipeline import fetch_real_prices
        prices = fetch_real_prices()
    except:
        pass
    
    holdings_value = 0
    for pos in portfolio["positions"]:
        symbol = pos["symbol"]
        current_price = prices.get(symbol, {}).get("price", pos["entry_price"])
        holdings_value += pos["quantity"] * current_price
    
    total_value = portfolio["cash"] + holdings_value
    if total_value > portfolio["max_value"]:
        portfolio["max_value"] = total_value
    if total_value < portfolio["min_value"]:
        portfolio["min_value"] = total_value
    
    drawdown = ((portfolio["max_value"] - total_value) / portfolio["max_value"] * 100) if portfolio["max_value"] > 0 else 0
    total_trades = portfolio["wins"] + portfolio["losses"]
    win_rate = (portfolio["wins"] / total_trades * 100) if total_trades > 0 else 0
    
    return jsonify({
        "cash": round(portfolio["cash"], 2),
        "holdings_value": round(holdings_value, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(portfolio["total_pnl"], 2),
        "win_rate": round(win_rate, 1),
        "drawdown": round(drawdown, 2),
        "trades": total_trades,
        "wins": portfolio["wins"],
        "losses": portfolio["losses"],
        "max_value": round(portfolio["max_value"], 2),
        "positions": portfolio["positions"],
        "recent_trades": portfolio["trades"][-20:]
    })


@app.route('/api/trade', methods=['POST'])
def execute_trade():
    data = request.get_json() or {}
    symbol = data.get("symbol")
    direction = data.get("direction", "buy")
    amount = float(data.get("amount", 100))
    stop_loss_pct = float(data.get("stop_loss", 5))
    take_profit_pct = float(data.get("take_profit", 15))
    
    if not symbol:
        return jsonify({"error": "Symbol required"}), 400
    
    # Get current price
    try:
        from brain.market_pipeline import fetch_real_prices
        prices = fetch_real_prices()
        price = prices.get(symbol, {}).get("price", None)
    except:
        price = None
    
    if not price:
        # Find asset in our list
        asset = next((a for a in ASSETS if a["symbol"] == symbol), None)
        if not asset:
            return jsonify({"error": "Unknown symbol"}), 400
        price = 100  # fallback
    
    if direction == "buy":
        if amount > portfolio["cash"]:
            return jsonify({"error": "Insufficient cash"}), 400
        
        quantity = amount / price
        portfolio["cash"] -= amount
        
        pos = {
            "symbol": symbol,
            "quantity": round(quantity, 8),
            "entry_price": round(price, 4),
            "amount": round(amount, 2),
            "stop_loss": round(price * (1 - stop_loss_pct / 100), 4),
            "take_profit": round(price * (1 + take_profit_pct / 100), 4),
            "opened_at": datetime.utcnow().isoformat()
        }
        portfolio["positions"].append(pos)
        save_portfolio()
        
        return jsonify({"success": True, "action": "buy", "position": pos})
    
    elif direction == "sell":
        # Find position by symbol
        idx = next((i for i, p in enumerate(portfolio["positions"]) if p["symbol"] == symbol), None)
        if idx is None:
            return jsonify({"error": "No position found for this symbol"}), 400
        
        pos = portfolio["positions"].pop(idx)
        revenue = pos["quantity"] * price
        pnl = revenue - pos["amount"]
        portfolio["cash"] += revenue
        portfolio["total_pnl"] += pnl
        
        if pnl > 0:
            portfolio["wins"] += 1
        else:
            portfolio["losses"] += 1
        
        trade = {
            "symbol": symbol,
            "entry_price": pos["entry_price"],
            "exit_price": round(price, 4),
            "quantity": pos["quantity"],
            "pnl": round(pnl, 2),
            "pnl_pct": round(((price - pos["entry_price"]) / pos["entry_price"]) * 100, 2),
            "type": "win" if pnl > 0 else "loss",
            "closed_at": datetime.utcnow().isoformat()
        }
        portfolio["trades"].append(trade)
        if len(portfolio["trades"]) > 500:
            portfolio["trades"] = portfolio["trades"][-500:]
        
        save_portfolio()
        
        return jsonify({"success": True, "action": "sell", "trade": trade})


@app.route('/api/portfolio/reset', methods=['POST'])
def reset_portfolio():
    global portfolio
    portfolio = {
        "cash": 10000.0,
        "positions": [],
        "trades": [],
        "total_pnl": 0.0,
        "wins": 0,
        "losses": 0,
        "max_value": 10000.0,
        "min_value": 10000.0
    }
    save_portfolio()
    return jsonify({"success": True, "message": "Portfolio reset to $10,000"})


@app.route('/api/brain/health')
def brain_health():
    return jsonify(brain.get_health())


@app.route('/api/brain/evolve', methods=['POST'])
def force_evolve():
    log = brain.evolve()
    return jsonify({"success": True, "log": log, "health": brain.get_health()})


@app.route('/api/brain/log')
def brain_log():
    return jsonify({
        "generation": brain.generation,
        "log": brain.evolution_log[-50:]
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

