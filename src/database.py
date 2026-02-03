from datetime import datetime, timedelta
import logging
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
from src.config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

    def write_rate(self, rate: float):
        try:
            point = Point("electricity_rate") \
                .tag("provider", "Holston Electric") \
                .field("price_per_kwh", float(rate)) \
                .time(datetime.utcnow())
            self.write_api.write(bucket=settings.INFLUXDB_BUCKET, org=settings.INFLUXDB_ORG, record=point)
            logger.info(f"Successfully wrote rate: {rate}")
        except Exception as e:
            logger.error(f"Failed to write rate to InfluxDB: {e}")
            raise

    def write_usage(self, timestamp_ms: int, usage_kwh: float):
        try:
            dt = datetime.utcfromtimestamp(timestamp_ms / 1000.0)
            
            point = Point("electricity_usage") \
                .tag("provider", "Holston Electric") \
                .field("kwh", float(usage_kwh)) \
                .time(dt)
            self.write_api.write(bucket=settings.INFLUXDB_BUCKET, org=settings.INFLUXDB_ORG, record=point)
            logger.info(f"Successfully wrote usage for {dt.strftime('%Y-%m-%d')}: {usage_kwh} kWh")
        except Exception as e:
            logger.error(f"Failed to write usage to InfluxDB: {e}")
            raise

    def get_average_usage(self, days: int = 7) -> float:
        query = f'''
        from(bucket: "{settings.INFLUXDB_BUCKET}")
          |> range(start: -{days}d)
          |> filter(fn: (r) => r["_measurement"] == "electricity_usage")
          |> filter(fn: (r) => r["_field"] == "kwh")
          |> mean()
        '''
        try:
            result = self.query_api.query(org=settings.INFLUXDB_ORG, query=query)
            if result and len(result) > 0 and len(result[0].records) > 0:
                return result[0].records[0].get_value()
            return 0.0
        except Exception as e:
            logger.error(f"Failed to query average usage: {e}")
            return 0.0

    def close(self):
        self.client.close()
