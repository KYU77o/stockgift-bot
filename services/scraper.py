import logging
from bs4 import BeautifulSoup
import requests
from datetime import datetime, date, timedelta
from models import db, Stock
import re
import time

logger = logging.getLogger(__name__)

class ScraperService:
    def _fetch_with_retry(self, url, headers, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
        return None

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
            response = self._fetch_with_retry(url, headers=headers)
            if not response:
                logger.error("Failed to fetch HiStock after retries.")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the main table: look for headers
            target_tables = []
            tables = soup.find_all('table')
            
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
                    target_tables.append((table, current_map))
                    logger.info(f"Found target table with columns: {current_map}")
            
            if not target_tables:
                logger.error("Could not find stock gift tables.")
                return []
                
            # Parse Rows across all matched tables
            for target_table, col_map in target_tables:
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
                            raw_text = id_cell.get_text(strip=True)
                            match = re.match(r'(\d{4,6})', raw_text)
                            if match:
                                stock_id = match.group(1)
                                stock_name = raw_text[len(stock_id):].strip()
                            else:
                                # Fallback
                                stock_id = raw_text[:4]
                                stock_name = raw_text[4:].strip()
                            
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
                            gift_cell = cells[col_map['gift']]
                            for a_tag in gift_cell.find_all('a'):
                                a_tag.decompose()
                            gift_name = gift_cell.get_text(strip=True)
                        
                        # Meeting Date
                        meeting_date = None
                        if 'meeting_date' in col_map and len(cells) > col_map['meeting_date']:
                            date_str = cells[col_map['meeting_date']].get_text(strip=True)
                            meeting_date = self._parse_date(date_str)

                        # Determine Gift Year from Meeting Date
                        # If meeting_date is parsed successfully, usage its year.
                        # Otherwise fallback to current year.
                        if meeting_date:
                            gift_year = meeting_date.year
                        else:
                            gift_year = datetime.now().year

                        # Last Buy Date
                        last_buy_date = None
                        if 'last_buy_date' in col_map and len(cells) > col_map['last_buy_date']:
                             date_str = cells[col_map['last_buy_date']].get_text(strip=True)
                             # Use the same smart parsing logic
                             last_buy_date = self._parse_date(date_str)
                        
                        # Cross-Year Logic Check (Refined)
                        # If Last Buy is Dec (12) and Meeting is Jan (1) of the SAME year (from simple parse),
                        # it means Last Buy should actually be the *previous* year.
                        # Example: system guessed both are 2027. But Buy is Dec, Meeting is Jan. 
                        # Then Buy is Dec 2026.
                        if last_buy_date and meeting_date:
                             # Case: Buy Month > Meeting Month + 6 (e.g. 12 > 1+6)
                             # Implicitly means Buy is late within a year cycle relative to Meeting, 
                             # which usually implies it belongs to the previous calendar year.
                            if last_buy_date.month > meeting_date.month + 6 and last_buy_date.year == meeting_date.year:
                                 last_buy_date = last_buy_date.replace(year=last_buy_date.year - 1)
                        
                        # Validation Check
                        if stock_id and gift_name and meeting_date:
                            results.append({
                                'stock_id': stock_id,
                                'name': stock_name,
                                'gift_name': gift_name,
                                'meeting_date': meeting_date,
                                'last_buy_date': last_buy_date,
                                'gift_year': gift_year
                            })
                            
                    except Exception as row_e:
                        logger.warning(f"Error parsing row: {row_e}")
                        continue
                    
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        # 去重：同一 stock_id 只保留一筆
        seen = {}
        for item in results:
            seen[item['stock_id']] = item
        unique_results = list(seen.values())

        logger.info(f"Scraped {len(results)} items, {len(unique_results)} unique from HiStock.")
        return unique_results

    def _parse_date(self, date_str):
        """
        Helper to parse dates with sustainable smart year detection.
        Formats: '115/06/15', '2026/06/15', '06/15'
        """
        if not date_str or date_str == '-' or date_str == '':
            return None
        
        try:
            today = date.today()
            current_year = today.year
            
            parts = date_str.split('/')
            
            # Case 1: MM/DD (Most common on HiStock table)
            if len(parts) == 2:
                month = int(parts[0])
                day = int(parts[1])
                
                # Smart Year Logic:
                # If today is Q4 (Oct-Dec) and target date is Q1 (Jan-Mar), assume Next Year.
                target_year = current_year
                if today.month >= 10 and month <= 3:
                     target_year += 1
                
                return date(target_year, month, day)

            # Case 2: YYY/MM/DD or YYYY/MM/DD
            elif len(parts) == 3:
                year = int(parts[0])
                if year < 1911: # ROC Year (e.g. 115)
                    year += 1911
                return date(year, int(parts[1]), int(parts[2]))
                
            return None
        except Exception as e:
            logger.warning(f"Date parse failed for '{date_str}': {e}")
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
                if data.get('name') and data['name'] != "Unknown":
                    stock.name = data['name']
                if data.get('gift_name'):
                    stock.gift_name = data['gift_name']
                if data.get('meeting_date'):
                    stock.meeting_date = data['meeting_date']
                if data.get('gift_year'):
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

    def cleanup_old_data(self):
        """
        Maintenance: Delete stocks with meeting dates older than 9 months.
        This prevents the database from exploding on the free tier.
        """
        try:
            # 9 months approx 270 days
            cutoff_date = date.today() - timedelta(days=270)
            
            deleted_count = Stock.query.filter(Stock.meeting_date < cutoff_date).delete()
            db.session.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleanup: Deleted {deleted_count} expired stocks (older than {cutoff_date}).")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Cleanup failed: {e}")

    def run(self):
        """
        Orchestrate scraping, saving, and cleanup.
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
            
        # Perform cleanup after update
        self.cleanup_old_data()
