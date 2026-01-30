from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi
from datetime import datetime, timedelta
import logging

from models import db, User, Stock
from utils.flex import create_stock_report
from services.scraper import ScraperService

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, app):
        self.app = app
        self.scheduler = BackgroundScheduler(timezone="Asia/Taipei")
        self.line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
        self.scraper = ScraperService() # Initialize scraper

    def start(self):
        # 1. Scrape Job (e.g., Mon 08:00 before broadcast)
        self.scheduler.add_job(
            self.scrape_job,
            'cron',
            day_of_week='mon',
            hour=8,
            minute=0,
            misfire_grace_time=3600
        )

        # 2. Broadcast Job (Mon 08:30)
        self.scheduler.add_job(
            self.broadcast_job, 
            'cron', 
            day_of_week='mon', 
            hour=8, 
            minute=30, 
            misfire_grace_time=3600
        )
        self.scheduler.start()
        logger.info("Scheduler started with Scrape(08:00) and Broadcast(08:30) jobs.")

    def scrape_job(self):
        logger.info("Starting scrape job...")
        with self.app.app_context():
            self.scraper.run()

    def broadcast_job(self, is_test=False):
        """
        Weekly Broadcast Job (Mon 08:30)
        is_test: If True, bypass date filter and broadcast upcoming stocks immediately.
        """
        logger.info(f"Starting broadcast job... (Test Mode: {is_test})")
        
        with self.app.app_context():
            stocks = []
            if is_test:
                # Test Mode: Fetch all stocks with future last buy dates (or recently passed)
                # To ensure the user sees something, we just fetch the top 20 upcoming/active ones.
                stocks = Stock.query.order_by(Stock.last_buy_date.desc()).limit(20).all()
            else:
                # Normal Mode: 
                # Notify for stocks that were ADDED or UPDATED in the past 7 days.
                # And ensure the "Last Buy Date" hasn't passed yet.
                today = datetime.now().date()
                one_week_ago = datetime.utcnow() - timedelta(days=7)
                
                stocks = Stock.query.filter(
                    Stock.updated_at >= one_week_ago,
                    Stock.last_buy_date >= today
                ).all()

            # Early Exit
            if not stocks:
                logger.info("No stocks found for broadcast.")
                if is_test:
                     # If DB is truly empty or no future dates, try fetching ANY stock to prove DB works
                     stocks = Stock.query.limit(5).all()
                     if not stocks:
                         return # DB is really empty
                else:
                    return

            # Batch Sending
            users = User.query.filter_by(is_active=True).all()
            user_ids = [u.line_user_id for u in users]
            
            if not user_ids:
                logger.info("No active users to notify.")
                return 

            logger.info(f"Found {len(stocks)} stocks and {len(user_ids)} users.")

            # Create Message
            message = create_stock_report(stocks)
            if not message:
                logger.error("Failed to create flex message.")
                return

            # Loop: Chunk users into batches of 500
            chunk_size = 500
            for i in range(0, len(user_ids), chunk_size):
                chunk = user_ids[i:i + chunk_size]
                try:
                    self.line_bot_api.multicast(chunk, message)
                    logger.info(f"Broadcasted to batch {i//chunk_size + 1}")
                except Exception as e:
                    logger.error(f"Failed to send batch {i}: {str(e)}")
