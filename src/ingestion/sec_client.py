import requests
import os
import json
from typing import Dict, Tuple, Optional
from src.ingestion.xbrl_normalizer import XBRLTaxonomyMapper

class SECDataFetcher:
    """Fetches and normalizes live XBRL financial facts from the SEC EDGAR API with local caching."""
    
    def __init__(self, user_agent: str = "LedgerLens Project ledgerlens@example.com", cache_dir: str = ".cache/sec_data"):
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self.tickers_url = "https://www.sec.gov/files/company_tickers.json"
        self.facts_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK{}.json"
        
        # Setup cache directory
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.cik_map = self._build_cik_map()
        self.mapper = XBRLTaxonomyMapper()

    def _build_cik_map(self) -> Dict[str, str]:
        """Maps standard ticker symbols (e.g., 'TSLA') to SEC CIK identifiers, using cache if available."""
        cache_path = os.path.join(self.cache_dir, "tickers.json")
        
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            resp = requests.get(self.tickers_url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
                
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}

    def _extract_annual_fact(self, concept_data: dict, target_year: int) -> Optional[float]:
            """Extracts the annual (10-K) value for a specific concept and year with priority on full-year filings."""
            if "units" not in concept_data or "USD" not in concept_data["units"]:
                return None
                
            facts = concept_data["units"]["USD"]
            
            # 1. Primary Filter: Full Fiscal Year annual filings (10-K or 10-K/A)
            annual_facts = [
                f for f in facts 
                if f.get("form") in ["10-K", "10-K/A"] 
                and f.get("fy") == target_year 
                and f.get("fp") == "FY"
            ]
            
            # 2. Fallback Filter: Match on form and fiscal year if fp is omitted
            if not annual_facts:
                annual_facts = [
                    f for f in facts 
                    if f.get("form") in ["10-K", "10-K/A"] 
                    and f.get("fy") == target_year
                ]
                
            if annual_facts:
                # Sort by filing date descending to capture the most recent audit/amendment
                annual_facts.sort(key=lambda x: x.get("filed", ""), reverse=True)
                return float(annual_facts[0].get("val", 0))
                
            return None

    def fetch_financials(self, ticker: str, target_year: int) -> Tuple[Dict[str, float], Dict[str, float]]:
        ticker = ticker.upper()
        if ticker not in self.cik_map:
            raise ValueError(f"Ticker {ticker} not found in SEC database.")
            
        cik = self.cik_map[ticker]
        cache_path = os.path.join(self.cache_dir, f"facts_{cik}.json")
        
        # Load from cache or fetch from SEC
        if os.path.exists(cache_path):
            print(f"Loading {ticker} financials from local cache...")
            with open(cache_path, "r", encoding="utf-8") as f:
                facts_data = json.load(f)
        else:
            print(f"Downloading {ticker} financials from SEC...")
            url = self.facts_url.format(cik)
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            facts_data = resp.json()
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(facts_data, f)
        
        us_gaap = facts_data.get("facts", {}).get("us-gaap", {})
        raw_cur, raw_prev = {}, {}
        
        for possible_tags in self.mapper.CONCEPT_MAPPINGS.values():
            for tag in possible_tags:
                if tag in us_gaap:
                    cur_val = self._extract_annual_fact(us_gaap[tag], target_year)
                    prev_val = self._extract_annual_fact(us_gaap[tag], target_year - 1)
                    if cur_val is not None: raw_cur[tag] = cur_val
                    if prev_val is not None: raw_prev[tag] = prev_val

        canonical_cur = self.mapper.normalize_facts(raw_cur)
        canonical_prev = self.mapper.normalize_facts(raw_prev)
        
        return canonical_cur, canonical_prev