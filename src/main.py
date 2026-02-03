import logging
import sys
from datetime import datetime, timedelta
from src.scraper import Scraper
from src.database import Database
from src.notifier import Notifier

import os
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Holston Electric Bot...")
    
    scraper = Scraper()
    db = Database()
    notifier = Notifier()

    try:
        try:
            rate = scraper.get_rate()
            db.write_rate(rate)
        except Exception as e:
            logger.error(f"Failed to process rate: {e}")
            rate = 0.0

        try:
            scraper.login()
            timestamp, usage = scraper.get_usage()
            
            db.write_usage(timestamp, usage)
            
            avg_usage = db.get_average_usage(days=7)
            
            from datetime import timezone
            date_str = datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc).strftime('%Y-%m-%d')
            
            est_cost = usage * rate if rate > 0 else 0.0
            
            notifier.notify_daily_report(rate, usage, date_str, est_cost)
            
            if avg_usage > 0 and usage > (avg_usage * 1.5):
                logger.info(f"Usage {usage} is significantly higher than average {avg_usage}. Sending alert.")
                notifier.notify_high_usage(usage, avg_usage, date_str)

        except Exception as e:
            logger.error(f"Failed to process usage: {e}")

    except Exception as e:
        logger.critical(f"Critical failure in main loop: {e}")
    finally:
        db.close()
        logger.info("Bot execution finished.")

if __name__ == "__main__":
    main()
