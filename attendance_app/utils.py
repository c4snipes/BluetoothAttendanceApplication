# utils.py

import logging
import requests

# Configure logging
logging.basicConfig(filename='application.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_message(message, level="info"):
    if level == "info":
        logging.info(message)
    elif level == "error":
        logging.error(message)
    else:
        logging.debug(message)

def is_valid_url(url):
    """
    Check if the given URL is valid and accessible.

    :param url: URL to check.
    :return: True if the URL is valid and accessible, False otherwise.
    """
    try:
        response = requests.get(url, allow_redirects=True, stream=True, timeout=5)
        return response.status_code == 200
    except Exception as e:
        log_message(f"Error validating URL {url}: {e}", "error")
        return False
