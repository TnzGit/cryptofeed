'''
Copyright (C) 2017-2022 Bryant Moscon - bmoscon@gmail.com

Please see the LICENSE file for the terms and conditions
associated with this software.
'''
from collections import defaultdict
from datetime import timezone, datetime as dt

import bson
import motor.motor_asyncio

from cryptofeed.backends.backend import BackendIntervalCallback, BackendBookCallback, BackendCallback, BackendQueue


class MongoCallback(BackendQueue):
    def __init__(self, db, host='127.0.0.1', port=27017, username=None, password=None, key=None, none_to=None, numeric_type=str, **kwargs):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db = db
        self.numeric_type = numeric_type
        self.none_to = none_to
        self.collection = key if key else self.default_key
        self.running = True

    async def writer(self):
        if self.username and self.password:
            uri = "mongodb://{username}:{password}@{host}:{port}".format(username=self.username, password=self.password, host=self.host, port=self.port)
        else:
            uri = "mongodb://{host}:{port}".format(host=self.host, port=self.port)
        conn = motor.motor_asyncio.AsyncIOMotorClient(uri)
        db = conn[self.db]
        while self.running:
            async with self.read_queue() as updates:
                for index in range(len(updates)):
                    updates[index]['timestamp'] = dt.fromtimestamp(updates[index]['timestamp'], tz=timezone.utc) if updates[index]['timestamp'] else None
                    updates[index]['receipt_timestamp'] = dt.fromtimestamp(updates[index]['receipt_timestamp'], tz=timezone.utc) if updates[index]['receipt_timestamp'] else None

                    if 'book' in updates[index]:
                        updates[index] = {'exchange': updates[index]['exchange'], 'symbol': updates[index]['symbol'], 'timestamp': updates[index]['timestamp'], 'receipt_timestamp': updates[index]['receipt_timestamp'], 'delta': 'delta' in updates[index], 'bid': bson.BSON.encode(updates[index]['book']['bid'] if 'delta' not in updates[index] else updates[index]['delta']['bid']), 'ask': bson.BSON.encode(updates[index]['book']['ask'] if 'delta' not in updates[index] else updates[index]['delta']['ask'])}

                await db[self.collection].insert_many(updates)


class TradeMongo(MongoCallback, BackendCallback):
    default_key = 'trades'


class FundingMongo(MongoCallback, BackendIntervalCallback):
    default_key = 'funding'

    def __init__(self, *args, snapshot_interval=60, **kwargs):
        self.snapshot_interval = snapshot_interval
        self.time_last_received = {}
        super().__init__(*args, **kwargs)


class BookMongo(MongoCallback, BackendBookCallback):
    default_key = 'book'

    def __init__(self, *args, snapshots_only=False, snapshot_interval=1000, **kwargs):
        self.snapshots_only = snapshots_only
        self.snapshot_interval = snapshot_interval
        self.snapshot_count = defaultdict(int)
        super().__init__(*args, **kwargs)


class TickerMongo(MongoCallback, BackendCallback):
    default_key = 'ticker'


class OpenInterestMongo(MongoCallback, BackendIntervalCallback):
    default_key = 'open_interest'
    def __init__(self, *args, snapshot_interval=60, **kwargs):
        self.snapshot_interval = snapshot_interval
        self.time_last_received = {}
        super().__init__(*args, **kwargs)

class LiquidationsMongo(MongoCallback, BackendCallback):
    default_key = 'liquidations'


class CandlesMongo(MongoCallback, BackendCallback):
    default_key = 'candles'
