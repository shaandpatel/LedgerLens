class XBRLTaxonomyMapper:
    """Handles taxonomy drift and deduplication of raw SEC XBRL facts."""
    
    CONCEPT_MAPPINGS = {
        "revenue": ["Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"],
        "inventory": ["InventoryNet", "Inventories"],
        "ar": ["AccountsReceivableNetCurrent", "AccountsAndNotesReceivableNet"],
        "deferred_revenue": ["ContractWithCustomerLiabilityCurrent", "DeferredRevenueCurrent"]
    }

    def normalize_facts(self, raw_facts: dict) -> dict:
        canonical = {}
        for canonical_name, possible_tags in self.CONCEPT_MAPPINGS.items():
            for tag in possible_tags:
                if tag in raw_facts:
                    canonical[canonical_name] = float(raw_facts[tag])
                    break # Prioritizes the first matching taxonomy tag
        return canonical