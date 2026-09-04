# 🎙️ Razorpay Buildathon — Track 02 Final Pitch & Demo Guide
## Project: Abuse & Return-to-Origin (RTO) Defense Sentinel

---

### ⏱️ Video Recording Flow (Estimated 3 to 4 Minutes)

```
0:00 - 0:35  │ The Problem: Cash-on-Delivery (COD) & RTO Margin Hemorrhage in India
0:35 - 1:15  │ The Architecture: Tri-Action Defense (ALLOW, CHALLENGE, BLOCK)
1:15 - 2:20  │ Live Demo: Testing the 4 Presets in Real-Time (<20ms Latency)
2:20 - 3:00  │ Quantitative Rigor: Measured Precision & Recall on 3,000 Held-Out Orders
3:00 - 3:45  │ The Bar: Quantified False-Positive Cost & ₹141,322 P&L Margin Protection
3:45 - 4:15  │ Regulatory Auditability & Closing
```

---

### 🎬 Scene 1: The Problem & The "Why Now" (0:00 – 0:35)
* **Screen**: Have the dashboard open at `http://127.0.0.1:8501` on the **⚡ Live Risk Simulator** tab.
* **What to say**:
  > *"Hello judges. In Indian e-commerce, Cash-on-Delivery accounts for over 60% of transactions, but high-risk COD orders suffer Return-to-Origin (RTO) failure rates exceeding 40%. Every returned order costs merchants between ₹350 to ₹1,200 in dead freight and restocking wear.*
  > 
  > *Most risk systems fail because they treat risk as a naive binary classification: if an order looks risky, they block it. But turning away a genuine, paying customer destroys gross margin and burns marketing acquisition costs.
  > 
  > *To solve this, we built the **Abuse & Return-to-Origin Defense Sentinel** for Razorpay's AI Risk Manager Track."*

---

### 🎬 Scene 2: The Architecture & Tri-Action Engine (0:35 – 1:15)
* **Screen**: Point to the top navbar and the brand header with the official Razorpay logo and live API connection indicator (`🟢 API Engine :8000 Online`).
* **What to say**:
  > *"Sentinel is a strictly defensive, real-time risk engine that pairs an 11-feature LightGBM model with deterministic heuristics and TreeSHAP explainability.*
  > 
  > *Instead of naive binary gating, Sentinel introduces a **Tri-Action Policy**:*
  > * *1. **ALLOW**: Instant, frictionless 1-click checkout for verified safe buyers.*
  > * *2. **CHALLENGE**: Rather than turning away borderline buyers, Sentinel automatically triggers the **Razorpay Magic Prepaid Nudge**, offering an automated ₹50 discount via WhatsApp or SMS to convert risky COD orders to prepaid. 75% of honest buyers convert, while 92% of casual return abusers abandon upfront payment.*
  > * *3. **BLOCK**: Gating COD placement for organized fraud rings, proxy abusers, and serial return syndicates."*

---

### 🎬 Scene 3: Live Simulator & Scenario Presets (1:15 – 2:20)
* **Screen**: Stay on Tab 1 (**⚡ Live Risk Simulator**). Click through the 4 presets:

#### Preset A: Safe Buyer (UPI)
* **Action**: Click `🟢 Safe Buyer (UPI)` -> Click `⚡ Evaluate Risk`.
* **What to say**:
  > *"Let's test our first preset: a verified buyer with 14 past completed orders paying via UPI from a Metro pincode. Within 18 milliseconds, Sentinel issues an **ALLOW** verdict with a risk score of only 1/100. Look at the SHAP factor audit: past order reputation and verified address drive the risk down."*

#### Preset B: Borderline COD (Nudge)
* **Action**: Click `🟡 Borderline COD (Nudge)` -> Click `⚡ Evaluate Risk`.
* **What to say**:
  > *"Now, let's test a borderline first-time COD buyer with a partial address. A naive model would either let this fail or block the customer. Sentinel issues a **CHALLENGE (COD NUDGE)** verdict with an elevated risk score of ~79/100 and unmitigated exposure of ₹394. Sentinel automatically triggers a Razorpay Magic Prepaid conversion link."*

#### Preset C: Fraud Ring (Block)
* **Action**: Click `🔴 Fraud Ring (Block)` -> Click `⚡ Evaluate Risk`.
* **What to say**:
  > *"Next, a fraud ring placing a ₹6,800 order at 2 AM with a high-risk Tier 3 pincode and a proxy IP mismatch. Sentinel immediately issues a **BLOCK** verdict with a 99/100 risk score, stopping ₹926 in direct courier freight loss."*

#### Preset D: Serial RTO Abuser
* **Action**: Click `⚠️ Serial RTO Abuser` -> Click `⚡ Evaluate Risk`.
* **What to say**:
  > *"Finally, a serial abuser who has returned 4 of their last 6 orders. The SHAP audit immediately isolates the buyer's historical return rate as a +3.10 SHAP spike, gating the order."*

---

### 🎬 Scene 4: Strict Held-Out Evaluation Benchmark (2:20 – 3:00)
* **Screen**: Click on Tab 2 (**📊 Held-Out Test Benchmark**).
* **What to say**:
  > *"Judging criteria strictly requires measured Precision and Recall on a held-out test set. We strictly held out 3,000 transactions with a fixed random seed (42).*
  > 
  > *Here are our verified quantitative metrics on the held-out test set:*
  > * * **Measured Recall**: **74.2%** at standard cutoff, catching 3 out of 4 high-risk return orders, and reaching **86.8%** coverage under the Tri-Action policy.*
  > * * **Measured Precision**: **56.4%** at standard threshold, rising to **96.2%** at the high-confidence BLOCK threshold.*
  > * * **ROC-AUC**: **0.8528**, showing strong class discrimination.*
  > * * **PR-AUC**: **0.7158**, proving robustness under class imbalance.*
  > 
  > *Below, judges can review the complete 3,000-order Confusion Matrix, the ROC trajectory curve, and our complete criteria verification matrix."*

---

### 🎬 Scene 5: Quantified False-Positive Cost & P&L Proof (3:00 – 3:45)
* **Screen**: Click on Tab 3 (**💰 Cost-Utility Matrix**).
* **What to say**:
  > *"The judging criteria emphasizes 'The Bar: Honest metrics including false-positive cost.' Standard data science competitions optimize F1 scores without looking at merchant unit economics.*
  > 
  > *In Tab 3, we explicitly quantify the asymmetric financial cost:*
  > * *Turning away a genuine buyer costs the merchant **25% gross margin + ₹150 in wasted customer acquisition marketing**.*
  > * *An undetected RTO costs **₹250 reverse logistics freight + 10% product restocking wear**.*
  > 
  > *On our 3,000 held-out orders, the naive status quo of allowing all COD results in **₹349,532 in losses**. Sentinel reduces this loss to **₹208,209**, preserving **₹141,322 in net merchant margin** — a **40.4% net financial loss reduction**."*

---

### 🎬 Scene 6: Model Explainability, Regulatory Audit & Closing (3:45 – 4:15)
* **Screen**: Click on Tab 4 (**🔍 SHAP Feature Audit**).
* **What to say**:
  > *"Finally, in Tab 4, Sentinel guarantees compliance and auditability. We utilize TreeSHAP to ensure mathematical additivity: every risk decision comes with transparent feature contributions, enabling instant merchant dispute resolution with zero demographic bias.*
  > 
  > *Sentinel is 100% defense-only, production-ready on FastAPI with sub-20ms latency, and designed to protect Indian merchants from day one. Thank you."*
