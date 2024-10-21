# scanner.py

import asyncio
import threading
import time
import logging
from bleak import BleakScanner  # Ensure Bleak is installed

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
            logging.info("Started Bluetooth scanning.")
        else:
            logging.warning("Scanning is already active.")

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.scan_devices())
        except Exception as e:
            logging.error(f"Asyncio loop encountered an error: {e}")
        finally:
            self.loop.close()

    def stop_scanning(self):
        """Stop scanning for Bluetooth devices."""
        if not self.scanning:
            logging.warning("Scanning is already stopped.")
            return
        self.scanning = False
        if self.loop and self.thread.is_alive():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.thread.join(timeout=5)  # Wait for the thread to finish
                if self.thread.is_alive():
                    logging.warning("Scanning thread did not terminate gracefully.")
                else:
                    logging.info("Scanning stopped gracefully.")
            except Exception as e:
                logging.error(f"Error stopping scanning: {e}")
        else:
            logging.warning("No active scanning thread found.")

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
                        addr_upper = device.address.upper()
                        found_devices[addr_upper] = {
                            'name': device.name,
                            'rssi': rssi,
                            'timestamp': current_time
                        }
                        logging.info(f"Found device: {device.name} ({device.address}) with RSSI: {rssi}")

                # Compare with previous_found_devices to detect changes
                if found_devices != previous_found_devices:
                    self.scan_devices_callback_wrapper(found_devices)
                    previous_found_devices = found_devices.copy()

            except Exception as e:
                logging.error(f"Error during scanning: {e}")
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
        logging.info(f"Updated RSSI threshold from {old_threshold} dBm to {new_threshold} dBm.")

    def update_scan_interval(self, new_interval):
        try:
            new_interval = int(new_interval)
            if new_interval < 1:
                raise ValueError("Scan interval must be at least 1 second.")
        except ValueError as ve:
            logging.error(f"Invalid scan interval update attempted: {ve}")
            return

        with self.lock:
            old_interval = self.scan_interval
            self.scan_interval = new_interval
        logging.info(f"Updated scan interval from {old_interval} seconds to {new_interval} seconds.")
