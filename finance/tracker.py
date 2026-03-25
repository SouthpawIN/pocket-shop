#!/usr/bin/env python3
"""Finance Tracker - Revenue tracking and splitting"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class FinanceTracker:
    """Track sales revenue and manage fund splits"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.data_path = Path("~/projects/pocket-shop/data/finance.json").expanduser()
        
        # Ensure data directory exists
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize file if it doesn't exist
        if not self.data_path.exists():
            self._initialize()
    
    def _initialize(self):
        """Initialize finance tracking file"""
        initial_data = {
            "savings_fund": 0.0,
            "profit_total": 0.0,
            "restock_fund": 0.0,
            "transactions": [],
            "initialized": datetime.now().isoformat(),
            "version": "1.0"
        }
        with open(self.data_path, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def _load_data(self) -> Dict:
        """Load finance data from file"""
        try:
            with open(self.data_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize()
            return self._load_data()
    
    def _save_data(self, data: Dict):
        """Save finance data to file"""
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_balances(self) -> Dict[str, float]:
        """Get current fund balances"""
        data = self._load_data()
        return {
            "savings_fund": data.get("savings_fund", 0.0),
            "profit_total": data.get("profit_total", 0.0),
            "restock_fund": data.get("restock_fund", 0.0)
        }
    
    def get_total_tracked(self) -> float:
        """Get total amount tracked across all funds"""
        balances = self.get_balances()
        return sum(balances.values())
    
    def add_sale(self, amount: float, card_name: str, 
                 source: str = "manual") -> Dict[str, float]:
        """Add a sale transaction and split the revenue"""
        
        # Get split ratios from config
        split_config = self.config.get('profit_split', {
            'savings': 0.30,
            'profit': 0.30,
            'restock': 0.40
        })
        
        # Calculate splits
        savings_add = amount * split_config['savings']
        profit_add = amount * split_config['profit']
        restock_add = amount * split_config['restock']
        
        # Load current data
        data = self._load_data()
        
        # Update balances
        data['savings_fund'] = data.get('savings_fund', 0.0) + savings_add
        data['profit_total'] = data.get('profit_total', 0.0) + profit_add
        data['restock_fund'] = data.get('restock_fund', 0.0) + restock_add
        
        # Add transaction record
        transaction = {
            "amount": amount,
            "card_name": card_name,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "splits": {
                "savings": savings_add,
                "profit": profit_add,
                "restock": restock_add
            }
        }
        data['transactions'].append(transaction)
        
        # Save updated data
        self._save_data(data)
        
        return {
            "savings": savings_add,
            "profit": profit_add,
            "restock": restock_add
        }
    
    def get_transactions(self, limit: int = None, 
                         start_date: str = None,
                         end_date: str = None) -> List[Dict]:
        """Get transaction history with optional filters"""
        data = self._load_data()
        transactions = data.get('transactions', [])
        
        # Apply date filters
        if start_date:
            transactions = [t for t in transactions 
                          if t.get('timestamp', '') >= start_date]
        if end_date:
            transactions = [t for t in transactions 
                          if t.get('timestamp', '') <= end_date]
        
        # Apply limit
        if limit:
            transactions = transactions[-limit:]
        
        return transactions
    
    def get_summary(self) -> Dict:
        """Get a summary of all financial data"""
        data = self._load_data()
        balances = self.get_balances()
        transactions = data.get('transactions', [])
        
        # Calculate totals from transactions
        total_sales = sum(t.get('amount', 0) for t in transactions)
        transaction_count = len(transactions)
        
        return {
            "balances": balances,
            "total_tracked": sum(balances.values()),
            "total_sales": total_sales,
            "transaction_count": transaction_count,
            "initialized": data.get('initialized'),
            "restock_target": self.config.get('restock_fund_target', 500.0)
        }
    
    def withdraw_from_fund(self, fund: str, amount: float, 
                          reason: str = "") -> bool:
        """Withdraw money from a specific fund"""
        if fund not in ['savings_fund', 'profit_total', 'restock_fund']:
            print(f"Invalid fund: {fund}")
            return False
        
        data = self._load_data()
        current_balance = data.get(fund, 0.0)
        
        if current_balance < amount:
            print(f"Insufficient funds in {fund}: ${current_balance:.2f} < ${amount:.2f}")
            return False
        
        # Deduct from fund
        data[fund] = current_balance - amount
        
        # Record withdrawal
        data['transactions'].append({
            "amount": -amount,  # Negative for withdrawal
            "card_name": f"WITHDRAWAL: {reason}",
            "source": "withdrawal",
            "timestamp": datetime.now().isoformat(),
            "from_fund": fund
        })
        
        self._save_data(data)
        return True
    
    def check_restock_target(self) -> Dict:
        """Check if restock fund has reached target"""
        target = self.config.get('restock_fund_target', 500.0)
        current = self.get_balances()['restock_fund']
        
        return {
            "target": target,
            "current": current,
            "remaining": target - current,
            "percentage": (current / target * 100) if target > 0 else 0,
            "reached": current >= target
        }
