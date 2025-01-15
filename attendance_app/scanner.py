# scanner.py

import asyncio
import threading
import time
import logging
from bleak import BleakScanner  

class Scanner:
    """
    A class that scans for nearby Bluetooth devices using the Bleak library on a background thread.
    """
    def __init__(self, callback=None, rssi_threshold=-70, scan_interval=10):
        """
        Initialize the Scanner.
        
        :param callback: A function to be called with the discovered devices (dict) whenever they change.
        :param rssi_threshold: The minimum RSSI required to include a device in found_devices.
                               RSSI stands for "Received Signal Strength Indicator," and
                               it is a measure of the signal power (in dBm). Higher (less negative)
                               means stronger signal. By default, -70 dBm is used; if a device's
                               RSSI is below (i.e., more negative than) -70, it's ignored.
        :param scan_interval: How many seconds to wait between scans.
        """
        self.callback = callback
        # The rssi_threshold is used to filter out devices with very weak signals.
        # Example: If rssi_threshold is -70, only devices at -69, -60, -50, etc. (stronger signals)
        #          are kept; devices at -71, -80, etc. are ignored.
        self.rssi_threshold = rssi_threshold
        self.scan_interval = scan_interval

        self.scanning = False
        self.loop = None
        self.thread = None
        self.lock = threading.Lock()
        # stop_event is used to tell the async loop to stop scanning when we want to stop.
        self.stop_event = asyncio.Future()

    def start_scanning(self):
        """Start scanning for Bluetooth devices, if not already scanning."""
        try:
            if not self.scanning:
                self.scanning = True
                self.loop = asyncio.new_event_loop()
                self.stop_event = asyncio.Future()  # Re-initialize stop_event
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()
                logging.info("Started Bluetooth scanning.")
            else:
                logging.warning("Scanning is already active.")
        except Exception as e:
            logging.error(f"Error starting scanning: {e}")

    def _run_loop(self):
        """
        The target function for our background thread.
        It sets up an asyncio event loop to run 'scan_devices' until stopped.
        """
        asyncio.set_event_loop(self.loop)
        try:
            if self.loop:
                self.loop.run_until_complete(self.scan_devices())
            else:
                logging.error("Event loop is not initialized.")
        except Exception as e:
            logging.error(f"Asyncio loop encountered an error: {e}")
        finally:
            if self.loop:
                self.loop.close()

    def stop_scanning(self):
        """Stop scanning for Bluetooth devices, if scanning is active."""
        try:
            if not self.scanning:
                logging.warning("Scanning is already stopped.")
                return
            self.scanning = False
            if self.loop and self.thread and self.thread.is_alive():
                try:
                    # Signal the scanning loop to stop via stop_event
                    self.loop.call_soon_threadsafe(self.stop_event.set_result, True)
                    # Cancel all pending tasks
                    pending = asyncio.all_tasks(loop=self.loop)
                    for task in pending:
                        task.cancel()
                    # Wait for the thread to finish
                    if self.thread:
                        self.thread.join(timeout=5)
                    if self.thread and self.thread.is_alive():
                        logging.warning("Scanning thread did not terminate gracefully.")
                    else:
                        logging.info("Scanning stopped gracefully.")
                except Exception as e:
                    logging.error(f"Error stopping scanning: {e}")
            else:
                logging.warning("No active scanning thread found.")
        except Exception as e:
            logging.error(f"Error in stop_scanning method: {e}")

    async def scan_devices(self):
        """
        Continuously scan for Bluetooth devices until stop_event is set.
        After each scan, discovered devices (that meet the RSSI threshold) are passed to self.callback.
        """
        previous_found_devices = {}
        try:
            while not self.stop_event.done():
                try:
                    found_devices = {}
                    # BleakScanner.discover() returns a list of BLEDevice objects
                    nearby_devices = await BleakScanner.discover()
                    current_time = time.time()

                    # Safely read rssi_threshold and scan_interval under lock
                    with self.lock:
                        rssi_threshold = self.rssi_threshold
                        scan_interval = self.scan_interval

                    for device in nearby_devices:
                        # device.rssi is the signal strength in dBm (negative numbers).
                        # More negative means weaker signal; e.g., -80 dBm is weaker than -70 dBm.
                        rssi = device.rssi

                        # Keep only devices that pass our threshold.
                        if rssi >= rssi_threshold:
                            addr_upper = device.address.upper()
                            found_devices[addr_upper] = {
                                'name': device.name,
                                'rssi': rssi,
                                'timestamp': current_time
                            }
                            logging.debug(f"Found device: {device.name} "
                                          f"({device.address}) with RSSI: {rssi}")

                    # Only invoke callback if discovered devices differ from the last scan
                    if found_devices != previous_found_devices:
                        self.scan_devices_callback_wrapper(found_devices)
                        previous_found_devices = found_devices.copy()

                except asyncio.CancelledError:
                    logging.info("Scanning task was cancelled.")
                    break
                except Exception as e:
                    logging.error(f"Error during scanning: {e}")
                finally:
                    await asyncio.sleep(scan_interval)
        except asyncio.CancelledError:
            logging.info("Scanning loop was cancelled.")
        except Exception as e:
            logging.error(f"Unexpected error in scanning loop: {e}")
        finally:
            logging.info("Exiting scanning loop.")

    def scan_devices_callback_wrapper(self, found_devices):
        """
        Invoke self.callback with the updated device dictionary.
        The actual scheduling on main GUI thread (if needed) is handled by the callback itself.
        """
        try:
            if self.callback:
                self.callback(found_devices)
        except Exception as e:
            logging.error(f"Error in scan_devices_callback_wrapper: {e}")

    def update_rssi_threshold(self, new_threshold):
        """
        Update the RSSI threshold (in dBm).
        If a device's signal is weaker (lower) than this value, it won't be included.
        """
        try:
            with self.lock:
                old_threshold = self.rssi_threshold
                self.rssi_threshold = new_threshold
            logging.info(f"Updated RSSI threshold from {old_threshold} dBm to {new_threshold} dBm.")
        except Exception as e:
            logging.error(f"Error updating RSSI threshold: {e}")

    def update_scan_interval(self, new_interval):
        """
        Update how many seconds to wait between scans.
        """
        try:
            new_interval = int(new_interval)
            if new_interval < 1:
                raise ValueError("Scan interval must be at least 1 second.")
            with self.lock:
                old_interval = self.scan_interval
                self.scan_interval = new_interval
            logging.info(f"Updated scan interval from {old_interval} seconds to {new_interval} seconds.")
        except ValueError as ve:
            logging.error(f"Invalid scan interval update attempted: {ve}")
        except Exception as e:
            logging.error(f"Error updating scan interval: {e}")
