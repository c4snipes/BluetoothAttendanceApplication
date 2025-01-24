# scanner.py
import threading
import time
import logging
import asyncio
from bleak import BleakScanner

class Scanner:
    """
    A simple scanner that starts a background thread and calls
    BleakScanner.discover(timeout=2) in a loop. There's NO graceful
    stop_scanning—once started, you must quit the entire app.
    """

    def __init__(self, callback=None, rssi_threshold=-70, scan_interval=10):
        """
        :param callback: Function to call when new devices are found.
                         Receives a dict { MAC_UPPER: {...}, ... }.
        :param rssi_threshold: Minimum RSSI (dBm) to include device in the results.
        :param scan_interval: Overall loop interval (seconds).
                              Each cycle: 2-second BLE scan + (scan_interval - 2) sleep.
        """
        self.callback = callback
        self.rssi_threshold = rssi_threshold
        self.scan_interval = scan_interval

        self.scanning = False
        self.thread = None

        # Lock if you want to change rssi_threshold or scan_interval safely on the fly.
        self.lock = threading.Lock()

    def start_scanning(self):
        """
        Start scanning in a background thread. If already running, logs a warning.
        """
        if self.scanning:
            logging.warning("Scanner is already running.")
            return

        self.scanning = True
        self.thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.thread.start()
        logging.info("Started indefinite scanning. Must quit the app to end scanning.")

    def stop_scanning(self):
        """
        No graceful stop is supported. You might call this from your GUI's
        'Stop Scanning' button to just warn the user, or do nothing.
        """
        logging.warning("Stop scanning is NOT supported. Please quit the application to end scanning.")

    def _scan_loop(self):
        """
        The background thread that does indefinite scanning:
          - For each cycle, we run a 2s Bleak discovery,
          - Filter devices by RSSI,
          - Call self.callback if anything changed,
          - Sleep the remainder of self.scan_interval (e.g. 8s if scan_interval=10),
          - Repeat until the process exits (or forcibly kills the thread).
        """
        previous_found = {}
        scan_count = 0

        while True:
            if not self.scanning:
                # If you ever did set self.scanning=False, we'd break here.
                # But in this design, we never do. The app must exit.
                logging.info("Scanner loop is exiting—scanning was disabled.")
                break

            # Short scanning with a 2-second timeout
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                devices = loop.run_until_complete(
                    BleakScanner.discover(timeout=2.0)
                )
            except Exception as e:
                logging.error(f"Bleak scanning error: {e}")
                devices = []
            finally:
                loop.close()

            # Grab current settings safely
            with self.lock:
                rssi_thresh = self.rssi_threshold
                interval = self.scan_interval

            # Filter discovered devices by RSSI
            found_devices = {}
            now = time.time()
            for dev in devices:
                if dev.rssi >= rssi_thresh:
                    mac_up = dev.address.upper()
                    found_devices[mac_up] = {
                        'name': dev.name,
                        'rssi': dev.rssi,
                        'timestamp': now,
                        'scan_count': scan_count
                    }

            # If changed, notify callback
            if found_devices != previous_found:
                previous_found = dict(found_devices)
                if self.callback:
                    try:
                        self.callback(found_devices)
                    except Exception as cb_err:
                        logging.error(f"Error in scanner callback: {cb_err}")

            scan_count += 1

            # Sleep the remainder of interval (minus 2s for scanning)
            remainder = interval - 2
            if remainder > 0:
                time.sleep(remainder)

        logging.info("Exiting scanner loop.")

    def update_rssi_threshold(self, new_val):
        """
        Thread-safe update to rssi_threshold.
        """
        with self.lock:
            old = self.rssi_threshold
            self.rssi_threshold = new_val
        logging.info(f"RSSI threshold changed from {old} to {new_val}.")

    def update_scan_interval(self, new_val):
        """
        Thread-safe update to scan_interval (must be >= 2 if you want the 2s scan).
        """
        try:
            n = int(new_val)
            if n < 2:
                raise ValueError("scan_interval must be >= 2.")
            with self.lock:
                old = self.scan_interval
                self.scan_interval = n
            logging.info(f"Scan interval changed from {old} to {n} seconds.")
        except ValueError as ve:
            logging.error(f"Invalid scan interval: {ve}")
