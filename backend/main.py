import os
import time
import json
import pickle
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import shap

from backend.schemas import RiskEvaluationRequest, RiskEvaluationResponse, RiskFactorDetail

app = FastAPI(
    title="Razorpay Abuse & RTO Defense Sentinel API",
    description="Production-ready defensive risk manager gating e-commerce COD and abuse transactions.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model state
MODEL_ARTIFACT = None
SHAP_EXPLAINER = None
EVALUATION_REPORT = None

@app.on_event("startup")
def load_artifacts():
    global MODEL_ARTIFACT, SHAP_EXPLAINER, EVALUATION_REPORT

    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    model_path = os.path.join(project_dir, 'model', 'risk_model.pkl')
    report_path = os.path.join(project_dir, 'model', 'evaluation_report.json')

    if not os.path.exists(model_path):
        raise RuntimeError(f"Risk model artifact not found at {model_path}. Run train.py first!")

    with open(model_path, 'rb') as f:
        MODEL_ARTIFACT = pickle.load(f)

    # Initialize SHAP TreeExplainer for fast local attributions
    SHAP_EXPLAINER = shap.TreeExplainer(MODEL_ARTIFACT['model'])

    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            EVALUATION_REPORT = json.load(f)

    print("[STARTUP] Model artifact and SHAP TreeExplainer loaded successfully.")

def transform_request_to_features(req: RiskEvaluationRequest):
    # Derived variables
    is_cod = 1 if req.payment_method == 'COD' else 0
    is_first_order = 1 if req.user_total_orders == 0 else 0
    user_rto_rate = round(req.user_rto_count / max(1, req.user_total_orders), 4) if req.user_total_orders > 0 else 0.0
    is_tier3 = 1 if req.pincode_risk_tier == 'TIER_3_HIGH_RISK' else 0
    cod_x_tier3 = is_cod * is_tier3
    cod_x_high_amount = 1 if (is_cod == 1 and req.order_amount > 3500) else 0
    velocity_per_order = round(req.device_order_velocity_24h / (req.user_total_orders + 1), 4)
    impulse_risk_factor = round((1.0 - req.address_completeness_score) * is_cod, 4)
    is_late_night = 1 if (1 <= req.order_hour <= 4) else 0

    pm_map = {'COD': 0, 'UPI': 1, 'CARD': 2, 'NETBANKING': 3}
    pincode_map = {'TIER_1_METRO': 0, 'TIER_2': 1, 'TIER_3_HIGH_RISK': 2}

    payment_method_code = pm_map.get(req.payment_method, 0)
    pincode_tier_code = pincode_map.get(req.pincode_risk_tier, 1)

    feature_dict = {
        'order_amount': req.order_amount,
        'payment_method_code': payment_method_code,
        'user_total_orders': req.user_total_orders,
        'user_rto_count': req.user_rto_count,
        'user_rto_rate': user_rto_rate,
        'is_first_order': is_first_order,
        'device_order_velocity_24h': req.device_order_velocity_24h,
        'pincode_tier_code': pincode_tier_code,
        'address_completeness_score': req.address_completeness_score,
        'ip_shipping_distance_tier': req.ip_shipping_distance_tier,
        'cart_item_count': req.cart_item_count,
        'order_hour': req.order_hour,
        'is_cod': is_cod,
        'cod_x_tier3': cod_x_tier3,
        'cod_x_high_amount': cod_x_high_amount,
        'velocity_per_order': velocity_per_order,
        'impulse_risk_factor': impulse_risk_factor,
        'is_late_night': is_late_night
    }

    feature_cols = MODEL_ARTIFACT['feature_cols']
    df = pd.DataFrame([feature_dict])[feature_cols]
    return df, feature_dict

def generate_human_description(feature: str, val: float, contrib: float, raw: dict):
    if feature == 'is_cod' or feature == 'payment_method_code':
        return f"Payment instrument COD carries elevated return propensity (+{contrib:.2f})" if raw.get('is_cod', 0) == 1 else "Prepaid payment strongly reduces payment default risk"
    elif feature == 'impulse_risk_factor':
        return f"Incomplete shipping address combined with COD indicates impulse/fake order (+{contrib:.2f})"
    elif feature == 'pincode_tier_code' or feature == 'cod_x_tier3':
        return f"Destination pincode is in high-risk COD cancellation tier (+{contrib:.2f})"
    elif feature == 'velocity_per_order' or feature == 'device_order_velocity_24h':
        return f"Device order velocity ({raw.get('device_order_velocity_24h')} in 24h) indicates abnormal ordering burst (+{contrib:.2f})"
    elif feature == 'user_rto_rate' or feature == 'user_rto_count':
        return f"Historical user abuse track record: {raw.get('user_rto_count')} prior RTOs (+{contrib:.2f})"
    elif feature == 'user_total_orders':
        return f"Established buyer with {raw.get('user_total_orders')} successful past deliveries" if raw.get('user_total_orders', 0) > 3 else "New or low-volume account with limited credit history"
    elif feature == 'cod_x_high_amount':
        return f"High-value COD order (Rs. {raw.get('order_amount'):,.2f}) has high doorstep refusal risk (+{contrib:.2f})"
    elif feature == 'ip_shipping_distance_tier':
        return "IP location deviates from delivery address or uses proxy/VPN"
    elif feature == 'is_late_night':
        return "Transaction placed during late-night hours (1 AM - 4 AM)"
    else:
        direction = "elevating" if contrib > 0 else "lowering"
        return f"Factor {feature} is {direction} transaction risk by {abs(contrib):.2f}"

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Razorpay AI Risk Manager Sentinel",
        "version": "1.0.0",
        "model_loaded": MODEL_ARTIFACT is not None
    }

@app.get("/v1/risk/metrics")
def get_model_metrics():
    if EVALUATION_REPORT is None:
        raise HTTPException(status_code=500, detail="Evaluation report not loaded")
    return EVALUATION_REPORT

@app.post("/v1/risk/evaluate", response_model=RiskEvaluationResponse)
def evaluate_transaction_risk(payload: RiskEvaluationRequest):
    start_time = time.perf_counter()

    if MODEL_ARTIFACT is None:
        raise HTTPException(status_code=503, detail="Model artifact not initialized")

    # Feature transformation
    X_df, raw_dict = transform_request_to_features(payload)

    # Predict risk probability
    prob = float(MODEL_ARTIFACT['model'].predict_proba(X_df)[0, 1])
    risk_score = round(prob, 4)

    # Local SHAP attributions
    shap_vals = SHAP_EXPLAINER.shap_values(X_df)
    if isinstance(shap_vals, list):
        row_shap = shap_vals[1][0]
    else:
        row_shap = shap_vals[0]

    feature_cols = MODEL_ARTIFACT['feature_cols']

    # Sort factors by absolute impact
    factor_indices = np.argsort(np.abs(row_shap))[::-1]
    top_risk_factors = []

    for idx in factor_indices[:5]:
        feat = feature_cols[idx]
        contrib = float(row_shap[idx])
        if abs(contrib) < 0.01:
            continue
        impact = "INCREASES_RISK" if contrib > 0 else "DECREASES_RISK"
        desc = generate_human_description(feat, X_df[feat].values[0], contrib, raw_dict)
        top_risk_factors.append(RiskFactorDetail(
            feature=feat,
            contribution=round(contrib, 4),
            impact=impact,
            description=desc
        ))

    # Threshold gating policy
    tau_low = MODEL_ARTIFACT['tau_low']
    tau_high = MODEL_ARTIFACT['tau_high']

    if risk_score < tau_low:
        decision = 'ALLOW'
        risk_tier = 'LOW'
        recommended_action = "Approve Instant Checkout: Low risk profile. Proceed with 1-click Razorpay Checkout."
    elif risk_score >= tau_high:
        decision = 'BLOCK'
        risk_tier = 'CRITICAL'
        recommended_action = "Gate Transaction: Critical abuse/fraud indicators detected. Block COD and require verified digital payment."
    else:
        decision = 'CHALLENGE'
        risk_tier = 'ELEVATED'
        recommended_action = "Trigger Razorpay Magic Prepaid Nudge: High RTO risk on COD. Send automated WhatsApp/SMS payment link offering Rs. 50 instant discount to convert order to prepaid or require OTP confirmation."

    # Expected unmitigated loss calculation
    # Reverse logistics + freight + restocking: Rs 250 + 10% of amount
    expected_loss = round(risk_score * (250.0 + (0.10 * payload.order_amount)), 2)

    latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return RiskEvaluationResponse(
        transaction_id=payload.order_id or "ord_mock_12345",
        decision=decision,
        risk_score=risk_score,
        risk_tier=risk_tier,
        thresholds={'tau_low': tau_low, 'tau_high': tau_high},
        expected_loss_if_unmitigated_inr=expected_loss,
        recommended_action=recommended_action,
        top_risk_factors=top_risk_factors,
        latency_ms=latency_ms
    )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
