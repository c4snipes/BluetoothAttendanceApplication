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
        :param rssi_threshold: The minimum RSSI required to include a device.
        :param scan_interval: How many seconds to wait between scans.
        """
        self.callback = callback
        self.rssi_threshold = rssi_threshold
        self.scan_interval = scan_interval

        self.scanning = False
        self.loop = None
        self.thread = None
        self.lock = threading.Lock()
        self.stop_event = None

    def start_scanning(self):
        """Start scanning for Bluetooth devices, if not already scanning."""
        try:
            if not self.scanning:
                self.scanning = True
                self.loop = asyncio.new_event_loop()
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()
                logging.info("Started Bluetooth scanning.")
            else:
                logging.warning("Scanning is already active.")
        except Exception as e:
            logging.error(f"Error starting scanning: {e}")

    async def _create_future(self):
        """Helper coroutine to create a Future in the event loop."""
        return asyncio.Future()


    def _run_loop(self):
        """
        The target function for our background thread.
        Sets up an asyncio event loop to run 'scan_devices' until stopped.
        """
        asyncio.set_event_loop(self.loop)
        self.stop_event = asyncio.Event()
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
                if self.stop_event is not None:
                        if self.loop:
                            self.loop.call_soon_threadsafe(self.stop_event.set)
                        else:
                            logging.error("Cannot stop scanning: Event loop is not initialized.")
            self.scanning = False
            if self.loop and self.thread and self.thread.is_alive():
                try:
                    if self.stop_event is not None:
                        self.loop.call_soon_threadsafe(self.stop_event.set)
                    pending = asyncio.all_tasks(loop=self.loop)
                    for task in pending:
                        task.cancel()
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
        After each scan, discovered devices (meeting the RSSI threshold) are passed to self.callback.
        """
        previous_found_devices = {}
        try:
            assert self.stop_event is not None, "stop_event is not initialized"
            while not self.stop_event.is_set():
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
                            logging.debug(f"Found device: {device.name} ({device.address}) with RSSI: {rssi}")

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
        """
        try:
            if self.callback:
                self.callback(found_devices)
        except Exception as e:
            logging.error(f"Error in scan_devices_callback_wrapper: {e}")

    def update_rssi_threshold(self, new_threshold):
        """
        Update the RSSI threshold.
        """
        with self.lock:
            self.rssi_threshold = new_threshold
        logging.info(f"RSSI threshold updated to {new_threshold} dBm.")

    def update_scan_interval(self, new_interval):
        """
        Update the scan interval.
        """
        with self.lock:
            self.scan_interval = new_interval
        logging.info(f"Scan interval updated to {new_interval} seconds.")
