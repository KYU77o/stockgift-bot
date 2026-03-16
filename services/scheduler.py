from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi
from datetime import datetime, timedelta, timezone
import logging

from models import db, User, Stock
from utils.flex import create_stock_reports
from services.scraper import ScraperService

logger = logging.getLogger(__name__)

def run_scrape_job(app):
    logger.info("Starting scrape job...")
    with app.app_context():
        scraper = ScraperService()
        scraper.run()

def run_broadcast_job(app, is_test=False, target_user_id=None):
    """
    Weekly Broadcast Job (Mon 08:30)
    is_test: If True, bypass date filter and broadcast upcoming stocks immediately.
    target_user_id: If set, ONLY send to this user (Safe Mode).
    """
    logger.info(f"Starting broadcast job... (Test: {is_test}, Target: {target_user_id})")
    
    with app.app_context():
        stocks = []
        if is_test:
            # Test Mode: Fetch top 20 upcoming stocks
            stocks = Stock.query.order_by(Stock.last_buy_date.desc()).limit(100).all()
        else:
            # Normal Mode: 
            # Notify for stocks that were ADDED or UPDATED in the past 7 days.
            TPE = timezone(timedelta(hours=8))
            today = datetime.now(TPE).date()
            one_week_ago = datetime.now(TPE) - timedelta(days=7)
            
            stocks = Stock.query.filter(
                Stock.updated_at >= one_week_ago,
                Stock.last_buy_date >= today
            ).all()

        # Early Exit
        if not stocks:
            logger.info("No stocks found for broadcast.")
            if is_test:
                 # Fallback to prove DB works
                 stocks = Stock.query.limit(5).all()
                 if not stocks:
                     return # DB is really empty
            else:
                return

        # Determine Recipients
        user_ids = []
        if target_user_id:
            # SAFE MODE: Only send to the admin/tester
            user_ids = [target_user_id]
            logger.info(f"SAFE MODE: Sending only to target user: {target_user_id}")
        else:
            # BROADCAST MODE: Send to ALL active users
            users = User.query.filter_by(is_active=True).all()
            user_ids = [u.line_user_id for u in users]

        if not user_ids:
            logger.info("No active users to notify.")
            return 

        logger.info(f"Found {len(stocks)} stocks and {len(user_ids)} users.")

        # Create Messages (Each message has 5 stocks)
        messages = create_stock_reports(stocks)
        if not messages:
            logger.error("Failed to create flex messages.")
            return

        # Batch Sending
        # LINE multicast allows up to 5 message objects per request, 
        # and up to 500 users per request.
        line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
        
        # 1. Chunk messages into groups of 5 max
        for m_idx in range(0, len(messages), 5):
            msg_chunk = messages[m_idx:m_idx + 5]
            
            # 2. Chunk users into groups of 500 max
            user_chunk_size = 500
            for u_idx in range(0, len(user_ids), user_chunk_size):
                u_chunk = user_ids[u_idx:u_idx + user_chunk_size]
                try:
                    line_bot_api.multicast(u_chunk, msg_chunk)
                    logger.info(f"Broadcasted msg {m_idx+1}-{m_idx+len(msg_chunk)} to users batch {u_idx//user_chunk_size + 1}")
                except Exception as e:
                    logger.error(f"Failed to send to batch {u_idx}: {str(e)}")

class SchedulerService:
    def __init__(self, app):
        self.app = app
        self.scheduler = BackgroundScheduler(timezone="Asia/Taipei")

    def start(self):
        # 1. Scrape Job (e.g., Mon 08:00 before broadcast)
        self.scheduler.add_job(
            run_scrape_job,
            'cron',
            args=[self.app],
            day_of_week='mon',
            hour=8,
            minute=0,
            misfire_grace_time=3600
        )

        # 2. Broadcast Job (Mon 08:30)
        self.scheduler.add_job(
            run_broadcast_job, 
            'cron', 
            args=[self.app],
            day_of_week='mon', 
            hour=8, 
            minute=30, 
            misfire_grace_time=3600
        )
        self.scheduler.start()
        logger.info("Scheduler started with Scrape(08:00) and Broadcast(08:30) jobs.")
