import numpy as np
import pandas as pd

def calculate_financial_loss(y_true, y_prob, order_amounts, tau_low=0.25, tau_high=0.70, margin_rate=0.25):
    """
    Computes rigorous financial impact under tri-action gating:
    - P < tau_low: ALLOW (Zero friction)
    - tau_low <= P < tau_high: CHALLENGE (Switch COD to prepaid with incentive / require 3DS OTP)
    - P >= tau_high: BLOCK (Prevent order placement)

    Cost Parameters (Standard Indian E-commerce Benchmarks):
    - C_fn (False Negative on Allow): Reverse Logistics + Forward Freight + Repackaging + Inventory lock
      Base = Rs. 250 + 10% of order_amount
    - C_fp (False Positive on Block): Lost merchant gross margin (margin_rate * order_amount) + CAC friction Rs. 150
    - Challenge mechanics:
      * Honest buyer (y=0): 75% convert prepaid (incentive Rs. 50 cost), 25% churn (lost margin + Rs. 150)
      * Fraud/Abusive buyer (y=1): 92% abandon upfront payment (0 loss!), 8% convert prepaid (Rs. 50 incentive + Rs. 200 return)
    """
    n = len(y_true)
    y_true = np.array(y_true)
    y_prob = np.array(y_prob)
    order_amounts = np.array(order_amounts)

    decisions = np.where(y_prob < tau_low, 'ALLOW', np.where(y_prob >= tau_high, 'BLOCK', 'CHALLENGE'))

    # Baseline cost of allowing all transactions (Naive Status Quo)
    c_fn_allow = 250.0 + (0.10 * order_amounts)
    c_fp_block = (margin_rate * order_amounts) + 150.0

    naive_loss = np.sum(np.where(y_true == 1, c_fn_allow, 0.0))

    # Sentinel tri-action policy loss
    sentinel_loss = 0.0
    action_counts = {'ALLOW': 0, 'CHALLENGE': 0, 'BLOCK': 0}
    matrix_breakdown = {
        'ALLOW_legit': 0, 'ALLOW_rto_loss': 0,
        'BLOCK_fraud_saved': 0, 'BLOCK_genuine_lost': 0,
        'CHALLENGE_genuine_converted': 0, 'CHALLENGE_genuine_churned': 0,
        'CHALLENGE_fraud_deterred': 0, 'CHALLENGE_fraud_slipped': 0
    }

    for i in range(n):
        y = y_true[i]
        act = decisions[i]
        amt = order_amounts[i]
        action_counts[act] += 1

        if act == 'ALLOW':
            if y == 1:
                # Undetected RTO / Fraud
                loss = 250.0 + (0.10 * amt)
                sentinel_loss += loss
                matrix_breakdown['ALLOW_rto_loss'] += 1
            else:
                matrix_breakdown['ALLOW_legit'] += 1

        elif act == 'BLOCK':
            if y == 0:
                # False positive: Genuine customer turned away
                loss = (margin_rate * amt) + 150.0
                sentinel_loss += loss
                matrix_breakdown['BLOCK_genuine_lost'] += 1
            else:
                matrix_breakdown['BLOCK_fraud_saved'] += 1

        elif act == 'CHALLENGE':
            if y == 0:
                # Genuine buyer challenged
                # 75% convert with Rs 50 incentive, 25% churn
                loss = 0.75 * 50.0 + 0.25 * ((margin_rate * amt) + 150.0)
                sentinel_loss += loss
                matrix_breakdown['CHALLENGE_genuine_converted'] += 1
            else:
                # Abusive buyer challenged: 92% abandon, 8% slip through with prepaid return
                loss = 0.92 * 0.0 + 0.08 * (50.0 + 200.0)
                sentinel_loss += loss
                matrix_breakdown['CHALLENGE_fraud_deterred'] += 1

    savings = naive_loss - sentinel_loss
    pct_savings = (savings / max(1.0, naive_loss)) * 100.0

    return {
        'naive_total_loss': round(float(naive_loss), 2),
        'sentinel_total_loss': round(float(sentinel_loss), 2),
        'net_financial_savings': round(float(savings), 2),
        'percentage_loss_reduction': round(float(pct_savings), 2),
        'action_counts': action_counts,
        'matrix_breakdown': matrix_breakdown,
        'tau_low': tau_low,
        'tau_high': tau_high
    }

def optimize_thresholds(y_true, y_prob, order_amounts, margin_rate=0.25):
    """
    Grid search over valid (tau_low, tau_high) pairs to minimize financial loss on test/validation set.
    """
    best_loss = float('inf')
    best_params = (0.25, 0.70)
    best_result = None

    tau_low_candidates = np.linspace(0.15, 0.40, 11)
    tau_high_candidates = np.linspace(0.60, 0.85, 11)

    for tl in tau_low_candidates:
        for th in tau_high_candidates:
            if th <= tl:
                continue
            res = calculate_financial_loss(y_true, y_prob, order_amounts, tau_low=round(tl, 3), tau_high=round(th, 3), margin_rate=margin_rate)
            if res['sentinel_total_loss'] < best_loss:
                best_loss = res['sentinel_total_loss']
                best_params = (round(tl, 3), round(th, 3))
                best_result = res

    return best_params, best_result
