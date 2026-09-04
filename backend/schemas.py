from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class RiskEvaluationRequest(BaseModel):
    order_id: Optional[str] = Field(default="ord_mock_12345", description="Unique Razorpay order ID")
    user_id: Optional[str] = Field(default="cust_demo_88", description="Customer ID / Contact identifier")
    order_amount: float = Field(..., gt=0, description="Order transaction amount in INR")
    payment_method: Literal['COD', 'UPI', 'CARD', 'NETBANKING'] = Field(..., description="Payment instrument")
    user_total_orders: int = Field(default=0, ge=0, description="Past completed orders by user")
    user_rto_count: int = Field(default=0, ge=0, description="Past RTO/abuse count on account")
    device_order_velocity_24h: int = Field(default=1, ge=1, description="Orders placed from device fingerprint in 24h")
    pincode_risk_tier: Literal['TIER_1_METRO', 'TIER_2', 'TIER_3_HIGH_RISK'] = Field(
        default='TIER_2', description="Delivery pincode logistics risk classification"
    )
    address_completeness_score: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Heuristic address quality score (0.0 to 1.0)"
    )
    ip_shipping_distance_tier: int = Field(
        default=0, ge=0, le=3, description="0: Same City, 1: Same State, 2: Diff State, 3: Proxy/VPN"
    )
    cart_item_count: int = Field(default=1, ge=1, description="Number of items in shopping cart")
    order_hour: int = Field(default=14, ge=0, le=23, description="Hour of transaction placement (0-23)")

class RiskFactorDetail(BaseModel):
    feature: str
    contribution: float
    impact: Literal['INCREASES_RISK', 'DECREASES_RISK']
    description: str

class RiskEvaluationResponse(BaseModel):
    transaction_id: str
    decision: Literal['ALLOW', 'CHALLENGE', 'BLOCK']
    risk_score: float
    risk_tier: Literal['LOW', 'ELEVATED', 'CRITICAL']
    thresholds: dict
    expected_loss_if_unmitigated_inr: float
    recommended_action: str
    top_risk_factors: List[RiskFactorDetail]
    latency_ms: float
