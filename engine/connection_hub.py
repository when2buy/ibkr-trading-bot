"""
ConnectionHub — singleton wrapper around ib_insync IB().
All strategies go through here; nobody else owns the IB() object.
"""
import asyncio, logging
from ib_insync import IB, util

logger = logging.getLogger('engine.hub')

class ConnectionHub:
    def __init__(self, host, port, client_id, account):
        self.host       = host
        self.port       = port
        self.client_id  = client_id
        self.account    = account
        self.ib         = IB()
        self._connected = False

        # wire internal reconnect
        self.ib.disconnectedEvent += self._on_disconnect

    # ── public ──────────────────────────────────────────────────────────────
    async def connect(self):
        for attempt in range(1, 6):
            try:
                await self.ib.connectAsync(self.host, self.port,
                                           clientId=self.client_id, timeout=10)
                self.ib.reqMarketDataType(3)   # delayed data OK
                self._connected = True
                logger.info(f"✅ Connected to IB Gateway ({self.host}:{self.port})")
                return
            except Exception as e:
                wait = 2 ** attempt
                logger.warning(f"Connection attempt {attempt} failed: {e} — retry in {wait}s")
                await asyncio.sleep(wait)
        raise ConnectionError("Could not connect to IB Gateway after 5 attempts")

    def disconnect(self):
        if self._connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IB Gateway")

    @property
    def is_connected(self):
        return self._connected and self.ib.isConnected()

    # ── internal ────────────────────────────────────────────────────────────
    def _on_disconnect(self):
        self._connected = False
        logger.warning("IB Gateway disconnected — scheduling reconnect")
        asyncio.ensure_future(self._reconnect())

    async def _reconnect(self):
        await asyncio.sleep(5)
        logger.info("Attempting reconnect...")
        await self.connect()
