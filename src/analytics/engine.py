from typing import Dict, List
from src.schemas import AnomalyTrigger

class SectorAwareAnalyticsEngine:
    def __init__(self, divergence_threshold: float = 0.15):
        self.threshold = divergence_threshold

    @staticmethod
    def calculate_yoy_growth(current: float, prior: float) -> float:
        return 0.0 if prior == 0 else (current - prior) / abs(prior)

    def evaluate_triggers(self, ticker: str, fiscal_year: int, sector: str, cur: Dict[str, float], prev: Dict[str, float]) -> List[AnomalyTrigger]:
        triggers = []
        rev_growth = self.calculate_yoy_growth(cur.get("revenue", 0), prev.get("revenue", 0))

        # 1. Retail / Manufacturing Specific Signals
        if sector in ["Manufacturing", "Retail", "Hardware"]:
            inv_growth = self.calculate_yoy_growth(cur.get("inventory", 0), prev.get("inventory", 0))
            if (inv_growth - rev_growth) > self.threshold:
                triggers.append(
                    AnomalyTrigger(
                        ticker=ticker, fiscal_year=fiscal_year,
                        trigger_type="INVENTORY_SALES_DIVERGENCE",
                        severity="CRITICAL" if (inv_growth - rev_growth) > 0.25 else "HIGH",
                        divergence_value=round(inv_growth - rev_growth, 4),
                        description=f"Inventory grew {inv_growth:.1%} YoY vs Revenue {rev_growth:.1%} YoY.",
                        sub_queries=["raw material cost inflation", "supply chain commitments", "inventory obsolescence write-down"]
                    )
                )

        # 2. SaaS / Software Specific Signals
        elif sector.lower() == "saas" or sector.lower() == "software & services":
            def_rev_growth = self.calculate_yoy_growth(cur.get("deferred_revenue", 0), prev.get("deferred_revenue", 0))
            if (rev_growth - def_rev_growth) > self.threshold:
                triggers.append(
                    AnomalyTrigger(
                        ticker=ticker, fiscal_year=fiscal_year,
                        trigger_type="DEFERRED_REVENUE_DECELERATION",
                        severity="HIGH",
                        divergence_value=round(rev_growth - def_rev_growth, 4),
                        description=f"Revenue grew {rev_growth:.1%} but Deferred Revenue grew only {def_rev_growth:.1%}.",
                        sub_queries=["billing milestones", "remaining performance obligations", "customer contract renewals"]
                    )
                )

        # 3. Universal Signals (AR / Revenue Divergence)
        ar_growth = self.calculate_yoy_growth(cur.get("ar", 0), prev.get("ar", 0))
        if (ar_growth - rev_growth) > self.threshold:
            triggers.append(
                AnomalyTrigger(
                    ticker=ticker, fiscal_year=fiscal_year,
                    trigger_type="RECEIVABLES_SALES_DIVERGENCE",
                    severity="HIGH",
                    divergence_value=round(ar_growth - rev_growth, 4),
                    description=f"AR grew {ar_growth:.1%} YoY vs Revenue {rev_growth:.1%} YoY.",
                    sub_queries=["allowance for doubtful accounts", "customer payment timing", "credit terms extended"]
                )
            )

        return triggers