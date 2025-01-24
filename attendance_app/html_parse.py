# html_parse.py

import re
import logging
import time
from bs4 import BeautifulSoup
import requests

def parse_html_file(html_file, valid_class_codes):
    """
    Parse an HTML file to extract classes/students. Return a dict of:
      { class_name: [ { 'name', 'student_id', 'email', 'photo_url'}, ... ], ... }

    We look for <h3> headings that match codes like "CSCI-101", then parse
    a subsequent <table> of students.
    """
    class_students = {}
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
    except Exception as e:
        logging.error(f"Failed to open/parse '{html_file}': {e}")
        return {}

    # Find headings that look like "CSCI-101", "MENG-250-01", etc.
    headings = soup.find_all('h3')
    pattern = r'\b(' + '|'.join(valid_class_codes) + r')-\d{3}(?:-\d+)?(?:-\w+)?\b'

    for heading in headings:
        raw_text = heading.get_text(strip=True)
        match = re.search(pattern, raw_text)
        if match:
            class_name = match.group(0)
        else:
            continue

        # The table that follows the heading should list student entries
        table = heading.find_next_sibling('table')
        if not table:
            logging.warning(f"No <table> after heading for '{class_name}'")
            continue

        # Example: <td width="180px"> each student
        tds = table.find_all('td', {'width': '180px'})
        st_list = []

        for td in tds:
            student = {}
            # If there's an <img> with src=..., use that as photo_url
            img_tag = td.find('img')
            if img_tag and 'src' in img_tag.attrs:
                student['photo_url'] = img_tag['src']
            else:
                student['photo_url'] = None

            # parse text inside the cell
            parts = td.get_text(separator='|').split('|')
            parts = [p.strip() for p in parts if p.strip()]

            # Typically, parts[0] = name, [1] = ID, [2] = email, etc.
            if len(parts) >= 1:
                student['name'] = parts[0]
            if len(parts) >= 2:
                student['student_id'] = parts[1]
            if len(parts) >= 3:
                student['email'] = parts[2]

            # If no explicit photo_url, try generating one
            if not student['photo_url']:
                maybe = generate_photo_url(student.get('name'), student.get('email'))
                student['photo_url'] = maybe or ""

            if 'name' not in student:
                logging.warning(f"Skipping entry with no name in {class_name}: {td}")
                continue

            st_list.append(student)

        if st_list:
            if class_name not in class_students:
                class_students[class_name] = []
            class_students[class_name].extend(st_list)

    return class_students

def is_valid_url(url, max_retries=3, backoff=1.0):
    """
    Return True if we can fetch the URL (HTTP 200). Otherwise False.
    Attempt up to `max_retries` times with a simple backoff.
    """
    if not url:
        return False

    for attempt in range(1, max_retries+1):
        try:
            resp = requests.get(url, allow_redirects=True, timeout=5)
            if resp.status_code == 200:
                return True
            else:
                logging.error(f"is_valid_url: '{url}' responded {resp.status_code}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt} for '{url}' failed: {e}")

        if attempt < max_retries:
            time.sleep(backoff)
            backoff *= 2  # exponential or fixed backoff, adjust as needed

    return False

def generate_photo_url(student_name, email=None):
    """
    Example logic to guess a directory photo URL based on student name or email.
    If none is found or all attempts fail, returns None.
    """
    if not student_name:
        return None

    try:
        parts = student_name.strip().split()
        if len(parts) >= 2:
            first = parts[0].lower()
            last = ''.join(parts[1:]).lower()
            first_initial = first[0]
            base_filename = f"{last}{first_initial}"
            base_url = f"https://directoryphotos.example.edu/{base_filename}"

            # Try base
            if is_valid_url(base_url):
                return base_url

            # Try numeric suffixes
            for i in range(1, 6):
                candidate = f"{base_url}{i}"
                if is_valid_url(candidate):
                    return candidate

        # Fallback: if email is known, try building a URL from the email prefix
        if email:
            prefix = email.split('@')[0]
            candidate = f"https://directoryphotos.example.edu/{prefix}"
            if is_valid_url(candidate):
                return candidate

        return None
    except Exception as e:
        logging.error(f"generate_photo_url failed for {student_name}: {e}")
        return None
