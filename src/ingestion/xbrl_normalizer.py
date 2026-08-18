from typing import Dict, Optional

class XBRLTaxonomyMapper:
    """Normalizes disparate US-GAAP taxonomy tags into canonical financial concepts."""
    
    CONCEPT_MAPPINGS = {
        "revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",  # Standard ASC 606 (MSFT, AAPL, AMZN, GOOG)
            "Revenues",                                            # Generic US-GAAP
            "SalesRevenueNet",                                     # Manufacturing / Industrial
            "SalesRevenueGoodsNet",                                # Goods-focused entities
            "OperatingRevenue",                                    # Services / Utilities
            "TotalRevenuesAndOtherIncome"                          # Financial / Diversified
        ],
        "inventory": [
            "InventoryNet",
            "InventoryGross",
            "Inventories"
        ],
        "ar": [
            "AccountsReceivableNetCurrent",
            "AccountsNotesAndLoansReceivableNetCurrent",
            "ReceivablesNetCurrent"
        ],
        "cogs": [
            "CostOfGoodsAndServicesSold",
            "CostOfRevenue",
            "CostOfGoodsSold"
        ],
        "deferred_revenue": [
            "DeferredRevenueCurrent",
            "ContractWithCustomerLiabilityCurrent",
            "ContractWithCustomerLiabilityRevenueRecognized"
        ]
    }

    def normalize_facts(self, raw_facts: Dict[str, float]) -> Dict[str, float]:
        """Maps raw GAAP tags to standardized canonical keys using priority order."""
        canonical = {}
        for canonical_name, possible_tags in self.CONCEPT_MAPPINGS.items():
            for tag in possible_tags:
                if tag in raw_facts and raw_facts[tag] is not None:
                    canonical[canonical_name] = raw_facts[tag]
                    break  # Take the highest-priority matching tag
            if canonical_name not in canonical:
                canonical[canonical_name] = 0.0
        return canonical