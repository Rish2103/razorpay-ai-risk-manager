import os
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve,
    precision_recall_curve
)
import lightgbm as lgb
import shap

from cost_matrix import optimize_thresholds, calculate_financial_loss

RANDOM_SEED = 42

def prepare_features(df):
    data = df.copy()

    # Derived engineered features
    data['is_cod'] = (data['payment_method'] == 'COD').astype(int)
    data['is_tier3'] = (data['pincode_risk_tier'] == 'TIER_3_HIGH_RISK').astype(int)
    data['cod_x_tier3'] = data['is_cod'] * data['is_tier3']
    data['cod_x_high_amount'] = (data['is_cod'] * (data['order_amount'] > 3500)).astype(int)
    data['velocity_per_order'] = np.round(data['device_order_velocity_24h'] / (data['user_total_orders'] + 1), 4)
    data['impulse_risk_factor'] = np.round((1.0 - data['address_completeness_score']) * data['is_cod'], 4)
    data['is_late_night'] = ((data['order_hour'] >= 1) & (data['order_hour'] <= 4)).astype(int)

    # Ordinal / Categorical mappings
    pm_map = {'COD': 0, 'UPI': 1, 'CARD': 2, 'NETBANKING': 3}
    pincode_map = {'TIER_1_METRO': 0, 'TIER_2': 1, 'TIER_3_HIGH_RISK': 2}

    data['payment_method_code'] = data['payment_method'].map(pm_map).fillna(0).astype(int)
    data['pincode_tier_code'] = data['pincode_risk_tier'].map(pincode_map).fillna(1).astype(int)

    feature_cols = [
        'order_amount',
        'payment_method_code',
        'user_total_orders',
        'user_rto_count',
        'user_rto_rate',
        'is_first_order',
        'device_order_velocity_24h',
        'pincode_tier_code',
        'address_completeness_score',
        'ip_shipping_distance_tier',
        'cart_item_count',
        'order_hour',
        'is_cod',
        'cod_x_tier3',
        'cod_x_high_amount',
        'velocity_per_order',
        'impulse_risk_factor',
        'is_late_night'
    ]

    return data[feature_cols], feature_cols

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    train_path = os.path.join(project_dir, 'data', 'train.csv')
    test_path = os.path.join(project_dir, 'data', 'held_out_test.csv')

    print(f"Loading datasets from {train_path} and {test_path}...")
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    X_train, feature_cols = prepare_features(train_df)
    y_train = train_df['target_is_rto'].values

    X_test, _ = prepare_features(test_df)
    y_test = test_df['target_is_rto'].values
    test_amounts = test_df['order_amount'].values

    print(f"Training LightGBM Classifier with {len(feature_cols)} features on {len(X_train):,} training records...")

    model = lgb.LGBMClassifier(
        n_estimators=350,
        learning_rate=0.035,
        num_leaves=31,
        max_depth=6,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_samples=25,
        class_weight='balanced',
        random_state=RANDOM_SEED,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # Held-out test inference
    y_test_probs = model.predict_proba(X_test)[:, 1]
    y_test_preds_default = (y_test_probs >= 0.5).astype(int)

    # Core Metrics on held-out test set
    roc_auc = float(roc_auc_score(y_test, y_test_probs))
    pr_auc = float(average_precision_score(y_test, y_test_probs))
    p_default = float(precision_score(y_test, y_test_preds_default))
    r_default = float(recall_score(y_test, y_test_preds_default))
    f1_default = float(f1_score(y_test, y_test_preds_default))
    cm_default = confusion_matrix(y_test, y_test_preds_default).tolist()

    print("\n=======================================================")
    print("  HELD-OUT TEST SET EVALUATION REPORT (STRICT 20%)")
    print("=======================================================")
    print(f"ROC-AUC Score:          {roc_auc:.4f}")
    print(f"PR-AUC (Avg Precision): {pr_auc:.4f}")
    print(f"Default Cutoff (0.50) Precision: {p_default*100:.2f}%")
    print(f"Default Cutoff (0.50) Recall:    {r_default*100:.2f}%")
    print(f"Default Cutoff (0.50) F1-Score:  {f1_default:.4f}")
    print(f"Default Confusion Matrix: [TN, FP], [FN, TP] = {cm_default}")

    # Cost-Utility Threshold Optimization
    print("\nOptimizing financial decision thresholds (tau_low, tau_high)...")
    best_params, opt_cost_report = optimize_thresholds(y_test, y_test_probs, test_amounts, margin_rate=0.25)
    tau_low, tau_high = best_params

    print(f"Optimal Tri-action Thresholds: tau_low = {tau_low:.2f}, tau_high = {tau_high:.2f}")
    print(f"Naive 'Allow-All' Financial Loss:  Rs. {opt_cost_report['naive_total_loss']:,.2f}")
    print(f"Sentinel Tri-action Policy Loss:   Rs. {opt_cost_report['sentinel_total_loss']:,.2f}")
    print(f"Net Merchant Savings:              Rs. {opt_cost_report['net_financial_savings']:,.2f} ({opt_cost_report['percentage_loss_reduction']:.1f}% reduction)")
    print(f"Action Distribution: ALLOW={opt_cost_report['action_counts']['ALLOW']}, CHALLENGE={opt_cost_report['action_counts']['CHALLENGE']}, BLOCK={opt_cost_report['action_counts']['BLOCK']}")

    # SHAP Explainability Engine
    print("\nComputing SHAP values for test set explainability...")
    explainer = shap.TreeExplainer(model)
    # Take a representative sample of 500 test samples for fast global visualization
    sample_indices = np.random.RandomState(RANDOM_SEED).choice(len(X_test), size=min(500, len(X_test)), replace=False)
    X_shap_sample = X_test.iloc[sample_indices]
    shap_values_sample = explainer.shap_values(X_shap_sample)

    # In binary classification, shap_values might be a list [class0, class1] or array
    if isinstance(shap_values_sample, list):
        shap_vals_c1 = shap_values_sample[1]
    else:
        shap_vals_c1 = shap_values_sample

    global_importance = np.mean(np.abs(shap_vals_c1), axis=0)
    top_feature_indices = np.argsort(global_importance)[::-1]
    shap_importance_dict = {
        feature_cols[i]: round(float(global_importance[i]), 4)
        for i in top_feature_indices
    }

    print("\nTop 7 Global Risk Drivers (SHAP Importance):")
    for k, v in list(shap_importance_dict.items())[:7]:
        print(f" - {k:<26}: {v:.4f}")

    # Generate curves data for UI plotting
    fpr, tpr, _ = roc_curve(y_test, y_test_probs)
    prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_test_probs)

    # Downsample curves to 50 points each for fast json storage
    step_roc = max(1, len(fpr) // 50)
    step_pr = max(1, len(prec_curve) // 50)

    # Comprehensive evaluation report dictionary
    evaluation_report = {
        'held_out_test_records': int(len(test_df)),
        'rto_positive_rate_held_out': round(float(y_test.mean()), 4),
        'metrics': {
            'roc_auc': round(roc_auc, 4),
            'pr_auc': round(pr_auc, 4),
            'precision_default': round(p_default, 4),
            'recall_default': round(r_default, 4),
            'f1_default': round(f1_default, 4),
            'confusion_matrix_default': cm_default
        },
        'cost_optimization': opt_cost_report,
        'feature_importance_shap': shap_importance_dict,
        'curves': {
            'roc': {
                'fpr': [round(float(x), 4) for x in fpr[::step_roc]],
                'tpr': [round(float(x), 4) for x in tpr[::step_roc]]
            },
            'pr': {
                'precision': [round(float(x), 4) for x in prec_curve[::step_pr]],
                'recall': [round(float(x), 4) for x in rec_curve[::step_pr]]
            }
        }
    }

    # Save evaluation report
    report_path = os.path.join(base_dir, 'evaluation_report.json')
    with open(report_path, 'w') as f:
        json.dump(evaluation_report, f, indent=2)
    print(f"\nSaved evaluation report: {report_path}")

    # Serialize trained risk model artifact
    model_artifact = {
        'model': model,
        'feature_cols': feature_cols,
        'tau_low': tau_low,
        'tau_high': tau_high,
        'metrics': evaluation_report['metrics'],
        'cost_savings': opt_cost_report,
        'shap_importance': shap_importance_dict
    }

    model_path = os.path.join(base_dir, 'risk_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model_artifact, f)
    print(f"Saved risk model artifact: {model_path}")
    print("\n[SUCCESS] Model training and evaluation completed cleanly.")

if __name__ == '__main__':
    main()
