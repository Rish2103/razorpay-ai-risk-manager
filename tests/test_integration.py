import os
import sys

# Ensure root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi.testclient import TestClient
import backend.main as b

b.load_artifacts()
client = TestClient(b.app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'healthy'
    assert data['model_loaded'] is True
    print("[PASS] Health check passed.")

def test_metrics_endpoint():
    r = client.get('/v1/risk/metrics')
    assert r.status_code == 200
    data = r.json()
    assert 'metrics' in data
    assert 'cost_optimization' in data
    assert data['metrics']['roc_auc'] >= 0.80
    print(f"[PASS] Metrics verified: ROC-AUC = {data['metrics']['roc_auc']:.4f}")

def test_safe_transaction():
    safe_payload = {
        'order_id': 'ord_safe_001',
        'user_id': 'cust_loyal_1',
        'order_amount': 1500.0,
        'payment_method': 'UPI',
        'user_total_orders': 15,
        'user_rto_count': 0,
        'device_order_velocity_24h': 1,
        'pincode_risk_tier': 'TIER_1_METRO',
        'address_completeness_score': 0.95,
        'ip_shipping_distance_tier': 0,
        'cart_item_count': 2,
        'order_hour': 14
    }
    r = client.post('/v1/risk/evaluate', json=safe_payload)
    assert r.status_code == 200
    res = r.json()
    assert res['decision'] == 'ALLOW'
    assert res['risk_score'] < 0.35
    print(f"[PASS] Safe transaction correctly ALLOWED (Score: {res['risk_score']:.4f}, Latency: {res['latency_ms']}ms)")

def test_fraud_transaction():
    fraud_payload = {
        'order_id': 'ord_fraud_002',
        'user_id': 'cust_abuser_2',
        'order_amount': 7500.0,
        'payment_method': 'COD',
        'user_total_orders': 0,
        'user_rto_count': 0,
        'device_order_velocity_24h': 5,
        'pincode_risk_tier': 'TIER_3_HIGH_RISK',
        'address_completeness_score': 0.25,
        'ip_shipping_distance_tier': 3,
        'cart_item_count': 4,
        'order_hour': 3
    }
    r = client.post('/v1/risk/evaluate', json=fraud_payload)
    assert r.status_code == 200
    res = r.json()
    assert res['decision'] == 'BLOCK'
    assert res['risk_score'] >= 0.85
    assert len(res['top_risk_factors']) > 0
    print(f"[PASS] Fraud transaction correctly BLOCKED (Score: {res['risk_score']:.4f}, Factors: {len(res['top_risk_factors'])})")

def test_borderline_challenge():
    border_payload = {
        'order_id': 'ord_border_003',
        'user_id': 'cust_border_3',
        'order_amount': 2200.0,
        'payment_method': 'COD',
        'user_total_orders': 1,
        'user_rto_count': 0,
        'device_order_velocity_24h': 2,
        'pincode_risk_tier': 'TIER_2',
        'address_completeness_score': 0.70,
        'ip_shipping_distance_tier': 1,
        'cart_item_count': 1,
        'order_hour': 19
    }
    r = client.post('/v1/risk/evaluate', json=border_payload)
    assert r.status_code == 200
    res = r.json()
    assert res['decision'] == 'CHALLENGE'
    assert 0.35 <= res['risk_score'] < 0.85
    print(f"[PASS] Borderline transaction correctly CHALLENGED (Score: {res['risk_score']:.4f})")

if __name__ == '__main__':
    print("Running Sentinel Integration Tests...")
    test_health()
    test_metrics_endpoint()
    test_safe_transaction()
    test_fraud_transaction()
    test_borderline_challenge()
    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")
