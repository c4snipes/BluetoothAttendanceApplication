# scanner.py

import asyncio
import threading
import time
from bleak import BleakScanner  # type: ignore
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
            log_message("Started Bluetooth scanning.", "info")

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.scan_devices())
        except Exception as e:
            log_message(f"Asyncio loop encountered an error: {e}", "error")
        finally:
            self.loop.close()

    def stop_scanning(self):
        """Stop scanning for Bluetooth devices."""
        if not self.scanning:
            return  # Already stopped
        self.scanning = False
        if self.loop and self.thread.is_alive():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=5)  # Wait for the thread to finish
            if self.thread.is_alive():
                log_message("Scanning thread did not terminate gracefully.", "warning")
            else:
                log_message("Scanning stopped gracefully.", "info")

    async def scan_devices(self):
        """Scan for Bluetooth devices and invoke the callback with results."""
        previous_found_devices = {}
        while self.scanning:
            try:
                found_devices = {}
                nearby_devices = await BleakScanner.discover()

                current_time = time.time()

                with self.lock:
                    rssi_threshold = self.rssi_threshold
                    scan_interval = self.scan_interval

                for device in nearby_devices:
                    rssi = device.rssi  

                    if rssi >= rssi_threshold:
                        found_devices[device.address.upper()] = {
                            'name': device.name,
                            'rssi': rssi,
                            'timestamp': current_time
                        }
                        log_message(f"Found device: {device.name} ({device.address}) with RSSI: {rssi}", "info")

                # Compare with previous_found_devices to detect changes
                if found_devices != previous_found_devices:
                    self.scan_devices_callback_wrapper(found_devices)
                    previous_found_devices = found_devices.copy()

            except Exception as e:
                log_message(f"Error during scanning: {e}", "error")
                # Decide whether to continue or halt scanning
            finally:
                with self.lock:
                    scan_interval = self.scan_interval
                await asyncio.sleep(scan_interval)

    def scan_devices_callback_wrapper(self, found_devices):
        """Wrapper to run the callback in a separate thread if it's not thread-safe."""
        if self.callback:
            threading.Thread(target=self.callback, args=(found_devices,), daemon=True).start()

    def update_rssi_threshold(self, new_threshold):
        with self.lock:
            old_threshold = self.rssi_threshold
            self.rssi_threshold = new_threshold
        log_message(f"Updated RSSI threshold from {old_threshold} dBm to {new_threshold} dBm.", "info")

    def update_scan_interval(self, new_interval):
        try:
            new_interval = int(new_interval)
            if new_interval < 1:
                raise ValueError("Scan interval must be at least 1 second.")
        except ValueError as ve:
            log_message(f"Invalid scan interval update attempted: {ve}", "error")
            return

        with self.lock:
            old_interval = self.scan_interval
            self.scan_interval = new_interval
        log_message(f"Updated scan interval from {old_interval} seconds to {new_interval} seconds.", "info")
