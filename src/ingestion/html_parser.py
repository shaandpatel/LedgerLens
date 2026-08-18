import requests
import os
import json
from bs4 import BeautifulSoup
import re
from typing import List
from src.schemas import DocumentChunk

class SECHTMLParser:
    """Fetches and parses live SEC 10-K HTML filings with local caching."""
    
    def __init__(self, user_agent: str = "LedgerLens Project ledgerlens@example.com", cache_dir: str = ".cache/sec_data"):
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_latest_10k_text(self, ticker: str, cik: str) -> str:
        """Fetches the most recent 10-K HTML, using local cache if available."""
        cache_path = os.path.join(self.cache_dir, f"{ticker}_latest_10k.html")
        
        # Check cache first
        if os.path.exists(cache_path):
            print(f"Loading {ticker} 10-K HTML from local cache...")
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()

        print(f"Downloading {ticker} 10-K HTML from SEC...")
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        resp = requests.get(submissions_url, headers=self.headers)
        resp.raise_for_status()
        
        filings = resp.json().get("filings", {}).get("recent", {})
        
        for idx, form in enumerate(filings.get("form", [])):
            if form == "10-K":
                accession_no = filings["accessionNumber"][idx].replace("-", "")
                document_name = filings["primaryDocument"][idx]
                
                html_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no}/{document_name}"
                doc_resp = requests.get(html_url, headers=self.headers)
                doc_resp.raise_for_status()
                
                html_text = doc_resp.text
                
                # Save to cache
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(html_text)
                    
                return html_text
                
        raise ValueError(f"No 10-K found for {ticker}")
    
    def fetch_10k_text_by_year(self, ticker: str, cik: str, target_year: int) -> str:
        """Fetches the 10-K HTML for a specific fiscal year, using local cache if available."""
        cache_path = os.path.join(self.cache_dir, f"{ticker}_{target_year}_10k.html")
        
        if os.path.exists(cache_path):
            print(f"Loading {ticker} {target_year} 10-K HTML from local cache...")
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()

        print(f"Downloading {ticker} {target_year} 10-K HTML from SEC...")
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        resp = requests.get(submissions_url, headers=self.headers)
        resp.raise_for_status()
        
        filings = resp.json().get("filings", {}).get("recent", {})
        
        for idx, form in enumerate(filings.get("form", [])):
            if form in ["10-K", "10-K/A"]:
                report_date = filings["reportDate"][idx]
                report_year = int(report_date.split("-")[0])
                
                # Match the fiscal year (SEC 10-Ks for year Y are usually filed early in year Y+1)
                if report_year == target_year or report_year == target_year + 1:
                    accession_no = filings["accessionNumber"][idx].replace("-", "")
                    document_name = filings["primaryDocument"][idx]
                    
                    html_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no}/{document_name}"
                    doc_resp = requests.get(html_url, headers=self.headers)
                    doc_resp.raise_for_status()
                    
                    html_text = doc_resp.text
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(html_text)
                        
                    return html_text
                    
        raise ValueError(f"No 10-K found for {ticker} matching year {target_year}")

    def extract_mda_section(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "lxml")
        text = soup.get_text(separator=" ", strip=True)
        text_lower = text.lower()
        
        start_pattern = re.compile(r"item\s+7\.\s+management")
        end_pattern = re.compile(r"item\s+8\.\s+financial\s+statements")
        
        start_match = list(start_pattern.finditer(text_lower))
        end_match = list(end_pattern.finditer(text_lower))
        
        if start_match and end_match:
            start_idx = start_match[-1].end()
            valid_ends = [m.start() for m in end_match if m.start() > start_idx]
            if valid_ends:
                end_idx = valid_ends[0]
                return text[start_idx:end_idx].strip()
        
        return text[:50000] 

    def chunk_text(self, text: str, ticker: str, section: str, chunk_size: int = 150) -> List[DocumentChunk]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{ticker}_{section}_{i//chunk_size}",
                    ticker=ticker,
                    section=section,
                    content=chunk_text
                )
            )
        return chunks