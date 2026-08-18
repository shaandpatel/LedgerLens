import argparse
import os
from pathlib import Path
from src.ingestion.sec_client import SECDataFetcher
from src.ingestion.html_parser import SECHTMLParser

def generate_labeling_view(ticker: str, year: int, output_dir: str = "data/labeling"):
    ticker = ticker.upper()
    print(f"Generating labeling view for {ticker} ({year} 10-K)...")
    
    # 1. Initialize clients
    fetcher = SECDataFetcher()
    parser = SECHTMLParser()
    
    # 2. Get CIK mapping
    if ticker not in fetcher.cik_map:
        print(f"Ticker {ticker} not found in SEC database.")
        return
    cik = fetcher.cik_map[ticker]
    
    try:
        # 3. Fetch year-targeted HTML and extract MD&A
        html_content = parser.fetch_10k_text_by_year(ticker, cik, year)
        mda_text = parser.extract_mda_section(html_content)
        chunks = parser.chunk_text(mda_text, ticker, section="MD&A")
        
    except Exception as e:
        print(f"Error processing {ticker} for {year}: {e}")
        return

    if not chunks:
        print("No chunks found.")
        return

    # 4. Output to Markdown
    os.makedirs(output_dir, exist_ok=True)
    output_file = Path(output_dir) / f"{ticker}_{year}_labeling_view.md"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"#Labeling View: {ticker} ({year} 10-K)\n")
        f.write("> Use `Ctrl+F` to find the anomaly discussion, then copy the `CHUNK ID` into your `investigation_cases.jsonl` expected_citations array.\n\n")
        f.write("---\n\n")
        
        for chunk in chunks:
            f.write(f"###CHUNK ID: `{chunk.chunk_id}`\n")
            f.write(f"{chunk.content}\n\n")
            f.write("---\n\n")
            
    print(f"Labeling view created successfully: {output_file}")

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Generate a year-targeted markdown file mapping SEC text to Chunk IDs.")
    arg_parser.add_argument("--ticker", type=str, required=True, help="Company ticker (e.g., TSLA)")
    arg_parser.add_argument("--year", type=int, required=True, help="Fiscal year (e.g., 2023)")
    
    args = arg_parser.parse_args()
    generate_labeling_view(args.ticker, args.year)