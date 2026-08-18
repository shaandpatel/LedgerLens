from src.analytics.engine import SectorAwareAnalyticsEngine
from src.ingestion.xbrl_normalizer import XBRLTaxonomyMapper

def test_xbrl_normalization():
    mapper = XBRLTaxonomyMapper()
    canonical = mapper.normalize_facts({"SalesRevenueNet": 100, "InventoryNet": 40})
    assert canonical["revenue"] == 100
    assert canonical["inventory"] == 40

def test_saas_vs_manufacturing_logic():
    engine = SectorAwareAnalyticsEngine(divergence_threshold=0.15)
    
    # Manufacturing gets Inventory trigger
    mfg_triggers = engine.evaluate_triggers("TSLA", 2025, "Manufacturing", {"revenue": 108.3, "inventory": 134.1}, {"revenue": 100.0, "inventory": 100.0})
    assert any(t.trigger_type == "INVENTORY_SALES_DIVERGENCE" for t in mfg_triggers)
    
    # SaaS ignores Inventory, flags Deferred Revenue deceleration
    saas_triggers = engine.evaluate_triggers("MSFT", 2025, "SaaS", {"revenue": 120.0, "deferred_revenue": 100.0, "inventory": 150.0}, {"revenue": 100.0, "deferred_revenue": 100.0, "inventory": 100.0})
    assert not any(t.trigger_type == "INVENTORY_SALES_DIVERGENCE" for t in saas_triggers)
    assert any(t.trigger_type == "DEFERRED_REVENUE_DECELERATION" for t in saas_triggers)