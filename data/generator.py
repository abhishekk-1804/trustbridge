import random
from datetime import datetime, timedelta
from database.models import (
    User, Account, Transaction,
    UserRole, TransactionType, TransactionStatus, PaymentMethod
)
from database.db import get_session_direct, init_db, reset_db

SEED = 42
random.seed(SEED)

MERCHANT_CATEGORIES = [
    "Food & Dining",
    "Transportation",
    "Shopping",
    "Utilities",
    "Entertainment",
    "Healthcare",
    "Education",
    "Groceries",
    "Fuel",
    "Online Services"
]

MERCHANT_NAMES = {
    "Food & Dining": ["Swiggy", "Zomato", "Local Restaurant", "Cafe Coffee Day", "McDonald's"],
    "Transportation": ["Uber", "Ola", "Rapido", "Metro", "Bus Service"],
    "Shopping": ["Amazon", "Flipkart", "Myntra", "Local Market", "Big Bazaar"],
    "Utilities": ["Electricity Bill", "Water Bill", "Internet Bill", "Mobile Recharge", "Gas Bill"],
    "Entertainment": ["Netflix", "Prime Video", "BookMyShow", "Gaming", "Spotify"],
    "Healthcare": ["Pharmacy", "Clinic", "Hospital", "Diagnostic Lab", "Dental"],
    "Education": ["Course Platform", "Books", "Certification", "Workshop", "Tuition"],
    "Groceries": ["BigBasket", "Blinkit", "Local Grocery", "DMart", "Reliance Fresh"],
    "Fuel": ["HP Petrol", "Indian Oil", "Bharat Petroleum", "Shell", "Essar"],
    "Online Services": ["Cloud Storage", "SaaS Subscription", "Domain Renewal", "API Service", "VPN"]
}

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow"
]

USER_PROFILES = [
    {
        "name": "Raj – Delivery Partner",
        "email": "raj.delivery@trustbridge.demo",
        "role": UserRole.DELIVERY_PARTNER,
        "avg_txn_amount": 1500,
        "txn_std": 500,
        "txn_frequency_days": 1,
        "failed_rate": 0.02,
        "anomaly_txn_idx": 120,
        "anomaly_multiplier": 8.0
    },
    {
        "name": "Priya – Freelancer",
        "email": "priya.freelancer@trustbridge.demo",
        "role": UserRole.FREELANCER,
        "avg_txn_amount": 3000,
        "txn_std": 1200,
        "txn_frequency_days": 2,
        "failed_rate": 0.01,
        "anomaly_txn_idx": 200,
        "anomaly_multiplier": 6.0
    },
    {
        "name": "Anil – Student",
        "email": "anil.student@trustbridge.demo",
        "role": UserRole.STUDENT,
        "avg_txn_amount": 800,
        "txn_std": 300,
        "txn_frequency_days": 3,
        "failed_rate": 0.03,
        "anomaly_txn_idx": 80,
        "anomaly_multiplier": 10.0
    }
]

TOTAL_TRANSACTIONS_TARGET = 400


def generate_transaction_amount(profile, txn_index):
    base_amount = random.gauss(profile["avg_txn_amount"], profile["txn_std"])
    base_amount = max(50, base_amount)

    if txn_index == profile["anomaly_txn_idx"]:
        base_amount *= profile["anomaly_multiplier"]
        return round(base_amount, 2), True, "AMOUNT_SPIKE"

    return round(base_amount, 2), False, None


def generate_merchant():
    category = random.choice(MERCHANT_CATEGORIES)
    name = random.choice(MERCHANT_NAMES[category])
    return category, name


def generate_transaction_type_and_status(profile):
    is_credit = random.random() < 0.15
    txn_type = TransactionType.CREDIT if is_credit else TransactionType.DEBIT

    is_failed = random.random() < profile["failed_rate"]
    status = TransactionStatus.FAILED if is_failed else TransactionStatus.SUCCESS

    return txn_type, status


def generate_user_transactions(session, user, account, profile, num_transactions, start_date):
    transactions = []
    current_date = start_date

    for i in range(num_transactions):
        amount, is_anomaly, anomaly_type = generate_transaction_amount(profile, i)
        txn_type, status = generate_transaction_type_and_status(profile)
        category, merchant = generate_merchant()
        city = random.choice(CITIES)
        payment_method = random.choice(list(PaymentMethod))

        if txn_type == TransactionType.DEBIT:
            description = f"Paid {amount} to {merchant} via {payment_method.value}"
        else:
            description = f"Received {amount} from {merchant} via {payment_method.value}"

        days_gap = max(0, int(random.gauss(profile["txn_frequency_days"], 0.5)))
        current_date += timedelta(days=days_gap, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        txn = Transaction(
            user_id=user.id,
            account_id=account.id,
            amount=amount,
            transaction_type=txn_type,
            status=status,
            payment_method=payment_method,
            merchant_category=category,
            merchant_name=merchant,
            location_city=city,
            description=description,
            timestamp=current_date,
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type
        )
        transactions.append(txn)

    return transactions


def generate_synthetic_data():
    reset_db()
    init_db()

    session = get_session_direct()

    try:
        users = []
        accounts = []
        all_transactions = []

        start_date = datetime(2024, 1, 1)
        txns_per_user = TOTAL_TRANSACTIONS_TARGET // len(USER_PROFILES)

        for profile_data in USER_PROFILES:
            user = User(
                name=profile_data["name"],
                email=profile_data["email"],
                role=profile_data["role"],
                account_created_at=start_date - timedelta(days=30),
                is_verified=True
            )
            session.add(user)
            session.flush()

            account = Account(
                user_id=user.id,
                account_type="savings",
                balance=random.uniform(10000, 50000),
                currency="INR",
                created_at=start_date - timedelta(days=30)
            )
            session.add(account)
            session.flush()

            users.append(user)
            accounts.append(account)

        session.commit()

        for user, account, profile_data in zip(users, accounts, USER_PROFILES):
            txns = generate_user_transactions(
                session, user, account, profile_data, txns_per_user, start_date
            )
            session.add_all(txns)
            all_transactions.extend(txns)

        session.commit()

        print(f"Generated {len(users)} users")
        print(f"Generated {len(accounts)} accounts")
        print(f"Generated {len(all_transactions)} transactions")

        anomaly_count = sum(1 for t in all_transactions if t.is_anomaly)
        print(f"Anomalies injected: {anomaly_count}")

        for txn in all_transactions:
            if txn.is_anomaly:
                print(f"  Anomaly: User {txn.user_id}, Txn {txn.id}, Amount Rs.{txn.amount}, Type: {txn.anomaly_type}")

    finally:
        session.close()


def get_user_transaction_counts():
    session = get_session_direct()
    try:
        from sqlalchemy import func
        counts = session.query(
            User.name,
            func.count(Transaction.id)
        ).join(Transaction).group_by(User.id).all()
        return dict(counts)
    finally:
        session.close()


if __name__ == "__main__":
    generate_synthetic_data()
    counts = get_user_transaction_counts()
    print("\nTransaction counts per user:")
    for name, count in counts.items():
        print(f"  {name}: {count}")