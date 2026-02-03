import logging
import requests
from .config import settings

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self):
        self.webhook_url = settings.DISCORD_WEBHOOK_URL

    def send_notification(self, title: str, message: str, color: int = 3447003):
        if not self.webhook_url:
            logger.warning("No Discord Webhook URL configured. Skipping notification.")
            return

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                    "footer": {
                        "text": "Holston Electric Bot"
                    }
                }
            ]
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Notification sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def notify_high_usage(self, current_usage: float, avg_usage: float, date_str: str):
        diff_percent = ((current_usage - avg_usage) / avg_usage) * 100 if avg_usage > 0 else 0
        
        title = "⚡ High Electricity Usage Alert"
        message = (
            f"**Date:** {date_str}\n"
            f"**Usage:** {current_usage:.2f} kWh\n"
            f"**7-Day Average:** {avg_usage:.2f} kWh\n"
            f"**Difference:** +{diff_percent:.1f}%"
        )
        self.send_notification(title, message, color=15158332)

    def notify_daily_report(self, rate: float, usage: float, date_str: str, cost: float):
        title = "⚡ Daily Electricity Report"
        message = (
            f"**Date:** {date_str}\n"
            f"**Rate:** ${rate:.5f}/kWh\n"
            f"**Usage:** {usage:.2f} kWh\n"
            f"**Est. Cost:** ${cost:.2f}"
        )
        self.send_notification(title, message, color=3066993)
