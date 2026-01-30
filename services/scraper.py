import logging
from bs4 import BeautifulSoup
import requests
from models import db, Stock

logger = logging.getLogger(__name__)

class ScraperService:
    def scrape_histock(self):
        """
        Primary Source: HiStock
        """
        url = "https://histock.tw/stock/gift.aspx"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        results = []
        try:
            logger.info(f"Fetching {url}...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the main table: look for headers
            target_table = None
            tables = soup.find_all('table')
            
            col_map = {}
            
            for table in tables:
                headers_row = table.find('tr')
                if not headers_row:
                    continue
                
                header_cells = [c.get_text(strip=True) for c in headers_row.find_all(['th', 'td'])]
                
                # Identify columns dynamically
                current_map = {}
                for idx, text in enumerate(header_cells):
                    if "代號" in text: current_map['id'] = idx
                    elif "名稱" in text: current_map['name'] = idx # Sometimes combined
                    elif "股東會紀念品" in text: current_map['gift'] = idx
                    elif "股東會日期" in text: current_map['meeting_date'] = idx
                    elif "最後買進日" in text: current_map['last_buy_date'] = idx
                
                # Check if this is the correct table (needs minimal fields)
                if 'gift' in current_map and ('id' in current_map or 'name' in current_map):
                    target_table = table
                    col_map = current_map
                    logger.info(f"Found target table with columns: {col_map}")
                    break
            
            if not target_table:
                logger.error("Could not find stock gift table.")
                return []
                
            # Parse Rows
            rows = target_table.find_all('tr')[1:] # Skip header
            for row in rows:
                cells = row.find_all('td')
                if not cells: continue
                
                try:
                    # Extract Data
                    # Handle Stock ID/Name - often combined or linked
                    stock_id = ""
                    stock_name = ""
                    
                    # Logic for ID column (often has <a> link)
                    if 'id' in col_map and len(cells) > col_map['id']:
                        id_cell = cells[col_map['id']]
                        # ID is likely 4 digits
                        stock_id = id_cell.get_text(strip=True)[:4] 
                        # Name might be in the same cell or separate
                        stock_name = id_cell.get_text(strip=True)[4:].strip()
                        
                        # Inspect link if present for cleaner ID
                        # (Not strictly needed if text parsing works)

                    # Logic for Name (if separate)
                    if not stock_name and 'name' in col_map and len(cells) > col_map['name']:
                         stock_name = cells[col_map['name']].get_text(strip=True)
                    
                    # Fallback name if empty (extract from link if possible)
                    if not stock_name:
                         stock_name = "Unknown"

                    # Gift Name
                    gift_name = ""
                    if 'gift' in col_map and len(cells) > col_map['gift']:
                        gift_name = cells[col_map['gift']].get_text(strip=True)
                    
                    # Meeting Date
                    meeting_date = None
                    if 'meeting_date' in col_map and len(cells) > col_map['meeting_date']:
                        date_str = cells[col_map['meeting_date']].get_text(strip=True)
                        # Parse date (e.g. 115/06/15 or 2026/06/15)
                        meeting_date = self._parse_date(date_str)

                    # Last Buy Date
                    last_buy_date = None
                    if 'last_buy_date' in col_map and len(cells) > col_map['last_buy_date']:
                         date_str = cells[col_map['last_buy_date']].get_text(strip=True)
                         last_buy_date = self._parse_date(date_str)
                    
                    # Validation Check
                    if stock_id and gift_name and meeting_date:
                        results.append({
                            'stock_id': stock_id,
                            'name': stock_name,
                            'gift_name': gift_name,
                            'meeting_date': meeting_date,
                            'last_buy_date': last_buy_date,
                            'gift_year': meeting_date.year if meeting_date else None
                        })
                        
                except Exception as row_e:
                    logger.warning(f"Error parsing row: {row_e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        logger.info(f"Scraped {len(results)} items from HiStock.")
        return results

    def _parse_date(self, date_str):
        """
        Helper to parse Taiwan/Western dates
        e.g. '112/05/20' -> 2023-05-20
             '2023/05/20' -> 2023-05-20
        """
        if not date_str or date_str == '-':
            return None
        try:
            from datetime import datetime
            
            # Handle 115/06/15 format
            parts = date_str.split('/')
            if len(parts) == 3:
                year = int(parts[0])
                if year < 1911: # ROC Year
                    year += 1911
                
                # Check year sanity (e.g., if parsing fails or bad data)
                if year < 2000 or year > 2100:
                    return None
                    
                return datetime(year, int(parts[1]), int(parts[2])).date()
                
            return None
        except:
            return None

    def scrape_wantgoo(self):
        """
        Backup Source: WantGoo
        Placeholder logic
        """
        logger.info("Scraping WantGoo...")
        return []

    def validate_data(self, stock_data):
        """
        Safety Logic:
        - If meeting_date or gift_name is empty/null, ABORT update for that stock.
        """
        if not stock_data.get('meeting_date'):
            logger.warning(f"Validation Failed: Missing meeting_date for {stock_data.get('stock_id')}")
            return False
        
        if not stock_data.get('gift_name'):
            logger.warning(f"Validation Failed: Missing gift_name for {stock_data.get('stock_id')}")
            return False
            
        return True

    def save_stocks(self, stocks_data):
        """
        Persist valid stocks to DB.
        Integrity: Never overwrite existing valid data with empty data.
        """
        count = 0
        for data in stocks_data:
            stock = Stock.query.get(data['stock_id'])
            if stock:
                # Update logic
                stock.name = data['name']
                stock.gift_name = data['gift_name']
                stock.meeting_date = data['meeting_date']
                stock.gift_year = data.get('gift_year')
                # Recalculate dates if needed
                if data.get('vote_start_date'):
                    stock.vote_start_date = data['vote_start_date']
                if data.get('last_buy_date'):
                    stock.last_buy_date = data['last_buy_date']
            else:
                # Insert
                stock = Stock(**data)
                db.session.add(stock)
            count += 1
        
        try:
            db.session.commit()
            logger.info(f"Saved {count} stocks to database.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit stocks: {e}")

    def run(self):
        """
        Orchestrate scraping and saving.
        """
        results = self.scrape_histock()
        
        if not results:
            logger.info("HiStock returned no data. Trying WantGoo...")
            results = self.scrape_wantgoo()
            
        valid_stocks = []
        for stock in results:
            if self.validate_data(stock):
                valid_stocks.append(stock)
        
        if valid_stocks:
            self.save_stocks(valid_stocks)
        else:
            logger.info("No valid stock data found to save.")
