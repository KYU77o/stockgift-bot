import logging
from bs4 import BeautifulSoup
import requests
from models import db, Stock

logger = logging.getLogger(__name__)

class ScraperService:
    def scrape_histock(self):
        """
        Primary Source: HiStock
        Placeholder logic
        """
        logger.info("Scraping HiStock...")
        # Mocking data return for structure
        return []

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
