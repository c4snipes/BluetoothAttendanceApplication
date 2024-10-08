# scanner.py

import asyncio
import threading
import time
from bleak import BleakScanner # type: ignore
from utils import log_message

class Scanner:
    def __init__(self, callback=None, rssi_threshold=-70, scan_interval=10):
        self.callback = callback
        self.rssi_threshold = rssi_threshold
        self.scan_interval = scan_interval
        self.scanning = False
        self.loop = None
        self.thread = None
        self.lock = threading.Lock()

    def start_scanning(self):
        """Start scanning for Bluetooth devices."""
        if not self.scanning:
            self.scanning = True
            self.loop = asyncio.new_event_loop()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.scan_devices())

    def stop_scanning(self):
        """Stop scanning for Bluetooth devices."""
        self.scanning = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

    async def scan_devices(self):
        """Scan for Bluetooth devices and invoke the callback with results."""
        while self.scanning:
            found_devices = {}
            nearby_devices = await BleakScanner.discover()

            current_time = time.time()

            with self.lock:
                rssi_threshold = self.rssi_threshold
                scan_interval = self.scan_interval

            for device in nearby_devices:
                if device.rssi >= rssi_threshold:
                    found_devices[device.address.upper()] = {
                        'name': device.name,
                        'rssi': device.rssi,
                        'timestamp': current_time
                    }
                    log_message(f"Found device: {device.name} ({device.address}) with RSSI: {device.rssi}", "info")

            if self.callback:
                self.callback(found_devices)

            await asyncio.sleep(scan_interval)

    def update_rssi_threshold(self, new_threshold):
        """Update the RSSI threshold."""
        with self.lock:
            self.rssi_threshold = new_threshold
        log_message(f"Updated RSSI threshold to {new_threshold} dBm", "info")

    def update_scan_interval(self, new_interval):
        """Update the scan interval."""
        with self.lock:
            self.scan_interval = new_interval
        log_message(f"Updated scan interval to {new_interval} seconds", "info")
