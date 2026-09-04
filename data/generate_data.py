import os
import random
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

def generate_synthetic_transactions(n_samples=15000):
    print(f"Generating {n_samples} realistic e-commerce transactions (Seed: {RANDOM_SEED})...")

    # Transaction identifiers
    order_ids = [f"ord_{np.random.randint(10000000, 99999999)}" for _ in range(n_samples)]
    user_ids = [f"cust_{np.random.randint(100000, 999999)}" for _ in range(n_samples)]

    # 1. User History
    is_new_user = np.random.binomial(1, 0.40, size=n_samples)
    user_total_orders = np.where(
        is_new_user == 1,
        0,
        np.random.negative_binomial(n=2, p=0.25, size=n_samples) + 1
    )
    user_total_orders = np.clip(user_total_orders, 0, 60)
    is_first_order = (user_total_orders == 0).astype(int)

    # Historical RTO count for returning users
    user_type_propensity = np.random.beta(0.4, 2.5, size=n_samples)
    user_rto_count = np.where(
        is_first_order == 1,
        0,
        np.random.binomial(n=np.maximum(1, user_total_orders), p=np.clip(user_type_propensity * 0.35, 0.0, 0.75))
    )
    user_rto_rate = np.where(user_total_orders > 0, user_rto_count / np.maximum(1, user_total_orders), 0.0)

    # 2. Payment Method: COD (48%), UPI (36%), CARD (12%), NETBANKING (4%)
    pm_choices = ['COD', 'UPI', 'CARD', 'NETBANKING']
    pm_probs = [0.48, 0.36, 0.12, 0.04]
    payment_method = np.random.choice(pm_choices, size=n_samples, p=pm_probs)
    is_cod = (payment_method == 'COD').astype(int)

    # 3. Order Amount (Log-normal in INR, median ~1600, range 249 to 32,000)
    raw_amount = np.random.lognormal(mean=7.1, sigma=0.75, size=n_samples)
    order_amount = np.round(np.clip(raw_amount, 249.0, 32000.0), 2)

    # 4. Pincode Risk Tier
    pincode_tiers = ['TIER_1_METRO', 'TIER_2', 'TIER_3_HIGH_RISK']
    pincode_tier = np.random.choice(pincode_tiers, size=n_samples, p=[0.42, 0.36, 0.22])

    # 5. Device Order Velocity (orders from device in 24h)
    device_order_velocity_24h = np.random.choice([1, 2, 3, 4, 5, 7], size=n_samples, p=[0.75, 0.15, 0.05, 0.03, 0.015, 0.005])

    # 6. Address Completeness Score (0.15 to 1.00)
    addr_base = np.random.beta(6.0, 1.8, size=n_samples)
    addr_penalty = np.where(pincode_tier == 'TIER_3_HIGH_RISK', np.random.uniform(0.05, 0.20, size=n_samples), 0.0)
    address_completeness_score = np.round(np.clip(addr_base - addr_penalty, 0.15, 1.0), 3)

    # 7. IP Distance / Mismatch Tier
    ip_mismatch_tier = np.random.choice([0, 1, 2, 3], size=n_samples, p=[0.55, 0.26, 0.15, 0.04])

    # 8. Cart Items & Order Hour
    cart_item_count = np.random.choice([1, 2, 3, 4, 5, 8], size=n_samples, p=[0.58, 0.24, 0.10, 0.05, 0.02, 0.01])
    order_hour = np.random.randint(0, 24, size=n_samples)
    is_late_night = ((order_hour >= 1) & (order_hour <= 4)).astype(int)

    # 9. Realistic Non-linear Logistic Model for Ground Truth
    # Canonical Indian D2C benchmark: COD RTO ~32-38%, Prepaid RTO ~6-9%, Total ~20-22%
    logit = -3.25

    # COD is dominant operational risk vector
    logit += 1.85 * is_cod

    # First time buyer without history
    logit += 0.55 * is_first_order

    # Prior RTO track record
    logit += 3.5 * user_rto_rate

    # Loyal verified buyer mitigation
    loyal_bonus = np.where((user_total_orders >= 4) & (user_rto_rate < 0.05), -1.8, 0.0)
    logit += loyal_bonus

    # Regional logistics risk
    pincode_weight = np.where(pincode_tier == 'TIER_3_HIGH_RISK', 1.15, np.where(pincode_tier == 'TIER_2', 0.25, -0.5))
    logit += pincode_weight

    # Address quality
    logit += 1.6 * (1.0 - address_completeness_score)

    # Velocity spike
    logit += 0.65 * np.maximum(0, device_order_velocity_24h - 1)

    # Proxy / VPN risk
    logit += np.where(ip_mismatch_tier == 3, 1.6, np.where(ip_mismatch_tier == 2, 0.3, 0.0))

    # Synergistic interaction vectors
    # High amount COD -> Doorstep buyer refusal
    high_value_cod = (is_cod == 1) & (order_amount > 3500)
    logit += 0.90 * high_value_cod.astype(float)

    # Remote pincode + COD
    tier3_cod = (is_cod == 1) & (pincode_tier == 'TIER_3_HIGH_RISK')
    logit += 0.75 * tier3_cod.astype(float)

    # Late night impulse COD
    logit += 0.35 * (is_late_night & is_cod)

    # High velocity first order (bot abuse)
    fraud_bot = (device_order_velocity_24h >= 3) & (is_first_order == 1)
    logit += 1.35 * fraud_bot.astype(float)

    # Stochastic variation
    noise = np.random.normal(0, 0.40, size=n_samples)
    logit += noise

    prob_rto = 1.0 / (1.0 + np.exp(-logit))
    target_is_rto = (np.random.rand(n_samples) < prob_rto).astype(int)

    df = pd.DataFrame({
        'order_id': order_ids,
        'user_id': user_ids,
        'order_amount': order_amount,
        'payment_method': payment_method,
        'user_total_orders': user_total_orders,
        'user_rto_count': user_rto_count,
        'user_rto_rate': np.round(user_rto_rate, 4),
        'is_first_order': is_first_order,
        'device_order_velocity_24h': device_order_velocity_24h,
        'pincode_risk_tier': pincode_tier,
        'address_completeness_score': address_completeness_score,
        'ip_shipping_distance_tier': ip_mismatch_tier,
        'cart_item_count': cart_item_count,
        'order_hour': order_hour,
        'target_is_rto': target_is_rto
    })

    return df

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    df = generate_synthetic_transactions(15000)

    print("\n=== Dataset Distribution ===")
    print(f"Total Transactions: {len(df):,}")
    print(f"Overall RTO Rate: {df['target_is_rto'].mean()*100:.2f}%")
    print(f"COD RTO Rate: {df[df['payment_method']=='COD']['target_is_rto'].mean()*100:.2f}%")
    print(f"Prepaid (UPI/Card/NB) RTO Rate: {df[df['payment_method']!='COD']['target_is_rto'].mean()*100:.2f}%")

    train_df, test_df = train_test_split(
        df,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=df['target_is_rto']
    )

    train_path = os.path.join(base_dir, 'train.csv')
    test_path = os.path.join(base_dir, 'held_out_test.csv')

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"\n[OK] Train dataset written: {train_path} ({len(train_df):,} records, RTO: {train_df['target_is_rto'].mean()*100:.2f}%)")
    print(f"[OK] Held-out test dataset written: {test_path} ({len(test_df):,} records, RTO: {test_df['target_is_rto'].mean()*100:.2f}%)")

if __name__ == '__main__':
    main()
