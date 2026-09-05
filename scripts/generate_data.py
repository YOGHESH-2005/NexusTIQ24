import os
import pandas as pd

SCENARIOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scenarios")

def create_scenarios():
    os.makedirs(SCENARIOS_DIR, exist_ok=True)

    # 1. Normal Customer Scenario
    normal_data = [
        {"transaction_id": "TXN-1001", "date": "2026-08-01", "time": "09:15:00", "description": "Grocery Store", "payee": "FreshMart", "amount": 2500.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-1002", "date": "2026-08-03", "time": "14:30:00", "description": "Electricity Bill", "payee": "State Power Corp", "amount": 4200.0, "channel": "NetBanking", "is_historical": True},
        {"transaction_id": "TXN-1003", "date": "2026-08-05", "time": "11:20:00", "description": "Coffee Shop", "payee": "Bean & Brew", "amount": 450.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-1004", "date": "2026-08-10", "time": "18:45:00", "description": "Fuel station", "payee": "Bharat Petroleum", "amount": 3100.0, "channel": "Card", "is_historical": True},
        {"transaction_id": "TXN-1005", "date": "2026-08-15", "time": "10:10:00", "description": "Supermarket", "payee": "FreshMart", "amount": 5800.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-1006", "date": "2026-08-20", "time": "16:00:00", "description": "Restaurant", "payee": "Spice Garden", "amount": 2200.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-1007", "date": "2026-08-25", "time": "12:30:00", "description": "Mobile Recharge", "payee": "Airtel Direct", "amount": 799.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-1008", "date": "2026-08-28", "time": "19:15:00", "description": "Bookstore", "payee": "PageTurner Books", "amount": 1500.0, "channel": "Card", "is_historical": True},
        # Current batch
        {"transaction_id": "TXN-1009", "date": "2026-09-01", "time": "10:00:00", "description": "Weekly Groceries", "payee": "FreshMart", "amount": 3400.0, "channel": "UPI", "is_historical": False},
        {"transaction_id": "TXN-1010", "date": "2026-09-03", "time": "15:20:00", "description": "Dining out", "payee": "Spice Garden", "amount": 2800.0, "channel": "UPI", "is_historical": False},
    ]
    pd.DataFrame(normal_data).to_csv(os.path.join(SCENARIOS_DIR, "normal_customer.csv"), index=False)

    # 2. Large Transfer Scenario (R01 Trigger)
    large_transfer_data = [
        {"transaction_id": "TXN-2001", "date": "2026-08-01", "time": "10:00:00", "description": "Salary Deposit", "payee": "TechCorp India", "amount": 14200.0, "channel": "NEFT", "is_historical": True},
        {"transaction_id": "TXN-2002", "date": "2026-08-05", "time": "11:30:00", "description": "Rent Payment", "payee": "Landlord Sharma", "amount": 15000.0, "channel": "NetBanking", "is_historical": True},
        {"transaction_id": "TXN-2003", "date": "2026-08-12", "time": "15:45:00", "description": "Groceries", "payee": "BigBasket", "amount": 3500.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-2004", "date": "2026-08-18", "time": "14:10:00", "description": "Utility Bill", "payee": "BESCOM Electric", "amount": 2800.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-2005", "date": "2026-08-25", "time": "17:00:00", "description": "Shopping", "payee": "Amazon India", "amount": 8400.0, "channel": "Card", "is_historical": True},
        # Current evaluation transaction (₹185,000 vs ~₹14,200 baseline median -> 13.03x)
        {"transaction_id": "TXN-2006", "date": "2026-09-04", "time": "14:30:00", "description": "Urgent Transfer", "payee": "Global Trading Co", "amount": 185000.0, "channel": "IMPS", "is_historical": False},
    ]
    pd.DataFrame(large_transfer_data).to_csv(os.path.join(SCENARIOS_DIR, "large_transfer.csv"), index=False)

    # 3. New Payee Burst Scenario (R02 Trigger)
    new_payee_data = [
        {"transaction_id": "TXN-3001", "date": "2026-08-02", "time": "09:30:00", "description": "Coffee Shop", "payee": "Starbucks", "amount": 650.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-3002", "date": "2026-08-10", "time": "14:15:00", "description": "Supermarket", "payee": "More Retail", "amount": 4100.0, "channel": "Card", "is_historical": True},
        {"transaction_id": "TXN-3003", "date": "2026-08-20", "time": "18:00:00", "description": "Fuel Station", "payee": "HPCL Petrol", "amount": 2500.0, "channel": "UPI", "is_historical": True},
        # Current burst to new payee "QuickMoney Services"
        {"transaction_id": "TXN-3004", "date": "2026-09-04", "time": "22:02:00", "description": "Service Fee 1", "payee": "QuickMoney Services", "amount": 75000.0, "channel": "IMPS", "is_historical": False},
        {"transaction_id": "TXN-3005", "date": "2026-09-04", "time": "22:08:00", "description": "Service Fee 2", "payee": "QuickMoney Services", "amount": 65000.0, "channel": "IMPS", "is_historical": False},
        {"transaction_id": "TXN-3006", "date": "2026-09-04", "time": "22:15:00", "description": "Service Fee 3", "payee": "QuickMoney Services", "amount": 45000.0, "channel": "IMPS", "is_historical": False},
    ]
    pd.DataFrame(new_payee_data).to_csv(os.path.join(SCENARIOS_DIR, "new_payee_burst.csv"), index=False)

    # 4. Odd Hours Activity Scenario (R03 Trigger)
    odd_hours_data = [
        {"transaction_id": "TXN-4001", "date": "2026-08-01", "time": "09:00:00", "description": "Breakfast", "payee": "South Tiffin", "amount": 200.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-4002", "date": "2026-08-05", "time": "13:00:00", "description": "Lunch", "payee": "Bistro 9", "amount": 1200.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-4003", "date": "2026-08-12", "time": "17:30:00", "description": "Groceries", "payee": "Reliance Fresh", "amount": 3500.0, "channel": "Card", "is_historical": True},
        {"transaction_id": "TXN-4004", "date": "2026-08-20", "time": "20:00:00", "description": "Dinner", "payee": "Olive Bistro", "amount": 2800.0, "channel": "Card", "is_historical": True},
        # Current evaluation transaction at 03:17 AM
        {"transaction_id": "TXN-4005", "date": "2026-09-04", "time": "03:17:00", "description": "Late Night Remittance", "payee": "Overseas Digital Ltd", "amount": 120000.0, "channel": "NetBanking", "is_historical": False},
    ]
    pd.DataFrame(odd_hours_data).to_csv(os.path.join(SCENARIOS_DIR, "odd_hours.csv"), index=False)

    # 5. Behaviour Deviation Scenario (R04 Trigger)
    behaviour_data = [
        {"transaction_id": "TXN-5001", "date": "2026-08-02", "time": "10:15:00", "description": "Morning Coffee", "payee": "CCD", "amount": 350.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-5002", "date": "2026-08-08", "time": "14:00:00", "description": "Cab Ride", "payee": "Uber India", "amount": 650.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-5003", "date": "2026-08-15", "time": "16:20:00", "description": "Department Store", "payee": "Shoppers Stop", "amount": 4500.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-5004", "date": "2026-08-22", "time": "11:45:00", "description": "Pharmacy", "payee": "Apollo Pharmacy", "amount": 1200.0, "channel": "UPI", "is_historical": True},
        # Current evaluation: ₹150,000 wire at 03:00 AM via IMPS to unknown payee (breaking amount, channel, time, payee pattern)
        {"transaction_id": "TXN-5005", "date": "2026-09-04", "time": "03:00:00", "description": "High Value Transfer", "payee": "Apex Ventures", "amount": 150000.0, "channel": "IMPS", "is_historical": False},
    ]
    pd.DataFrame(behaviour_data).to_csv(os.path.join(SCENARIOS_DIR, "behaviour_deviation.csv"), index=False)

    # 6. Multiple Risk Signals Scenario (R01 + R02 + R03 Triggered)
    multi_rule_data = [
        {"transaction_id": "TXN-6001", "date": "2026-08-01", "time": "11:00:00", "description": "Routine Groceries", "payee": "Nature Basket", "amount": 3200.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-6002", "date": "2026-08-10", "time": "15:30:00", "description": "Utility Payment", "payee": "Airtel Broadband", "amount": 1500.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-6003", "date": "2026-08-20", "time": "17:00:00", "description": "Clothing Store", "payee": "Zudio", "amount": 2800.0, "channel": "Card", "is_historical": True},
        # Current multi-rule triggers:
        # TXN-6004: ₹185,000 (R01 large transfer, R02 new payee, R03 odd hours at 03:15 AM)
        {"transaction_id": "TXN-6004", "date": "2026-09-04", "time": "03:15:00", "description": "Emergency Transfer 1", "payee": "QuickMoney Services", "amount": 185000.0, "channel": "IMPS", "is_historical": False},
        {"transaction_id": "TXN-6005", "date": "2026-09-04", "time": "03:22:00", "description": "Emergency Transfer 2", "payee": "QuickMoney Services", "amount": 75000.0, "channel": "IMPS", "is_historical": False},
        {"transaction_id": "TXN-6006", "date": "2026-09-04", "time": "03:30:00", "description": "Emergency Transfer 3", "payee": "QuickMoney Services", "amount": 45000.0, "channel": "IMPS", "is_historical": False},
    ]
    pd.DataFrame(multi_rule_data).to_csv(os.path.join(SCENARIOS_DIR, "multiple_rules.csv"), index=False)

    # 7. Incomplete Data Scenario (Missing payee, missing timestamp)
    incomplete_data = [
        {"transaction_id": "TXN-7000", "date": "2026-07-25", "time": "12:00:00", "description": "Utility Bill", "payee": "BESCOM", "amount": 1500.0, "channel": "NetBanking", "is_historical": True},
        {"transaction_id": "TXN-7001", "date": "2026-08-01", "time": "10:00:00", "description": "Supermarket", "payee": "FreshMart", "amount": 3000.0, "channel": "UPI", "is_historical": True},
        {"transaction_id": "TXN-7002", "date": "2026-08-10", "time": "14:00:00", "description": "Fuel", "payee": "Shell Petrol", "amount": 2500.0, "channel": "Card", "is_historical": True},
        # Current row missing payee
        {"transaction_id": "TXN-7003", "date": "2026-09-04", "time": "11:20:00", "description": "Unknown Withdrawal", "payee": "", "amount": 95000.0, "channel": "ATM", "is_historical": False},
        # Current row missing timestamp
        {"transaction_id": "TXN-7004", "date": "2026-09-04", "time": "", "description": "Unspecified Payment", "payee": "Vendor X", "amount": 40000.0, "channel": "UPI", "is_historical": False},
    ]
    pd.DataFrame(incomplete_data).to_csv(os.path.join(SCENARIOS_DIR, "incomplete_data.csv"), index=False)

    # 8. Contradictory Data Scenario (Amount discrepancy between transaction payload and secondary record flag)
    contradictory_data = [
        {"transaction_id": "TXN-8001", "date": "2026-08-01", "time": "10:00:00", "description": "Salary Credit", "payee": "Tech Global", "amount": 50000.0, "channel": "NEFT", "is_historical": True, "secondary_amount_record": 50000.0},
        {"transaction_id": "TXN-8002", "date": "2026-08-15", "time": "14:30:00", "description": "Rent", "payee": "House Owner", "amount": 18000.0, "channel": "NetBanking", "is_historical": True, "secondary_amount_record": 18000.0},
        # Current row: transaction amount ₹50,000, secondary ledger record ₹5,000 (Data Conflict!)
        {"transaction_id": "TXN-8003", "date": "2026-09-04", "time": "16:00:00", "description": "Vendor Clearing", "payee": "Unverified Supplier", "amount": 50000.0, "channel": "IMPS", "is_historical": False, "secondary_amount_record": 5000.0},
    ]
    pd.DataFrame(contradictory_data).to_csv(os.path.join(SCENARIOS_DIR, "contradictory_data.csv"), index=False)

    # 9. Insufficient History Scenario (Only 1 past transaction)
    insufficient_history_data = [
        {"transaction_id": "TXN-9001", "date": "2026-08-28", "time": "12:00:00", "description": "Account Opening Test", "payee": "Self Deposit", "amount": 1000.0, "channel": "UPI", "is_historical": True},
        # Current evaluation transaction
        {"transaction_id": "TXN-9002", "date": "2026-09-04", "time": "15:00:00", "description": "High Value Outflow", "payee": "Merchant Inc", "amount": 85000.0, "channel": "IMPS", "is_historical": False},
    ]
    pd.DataFrame(insufficient_history_data).to_csv(os.path.join(SCENARIOS_DIR, "insufficient_history.csv"), index=False)

    print("All 9 synthetic scenarios generated successfully in data/scenarios/")

if __name__ == "__main__":
    create_scenarios()
