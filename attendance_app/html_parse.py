# html_parse.py

import re
import logging
from bs4 import BeautifulSoup
import requests

def parse_html_file(html_file, valid_class_codes):
    """
    Parse an HTML file to extract class and student information.

    :param html_file: Path to the HTML file to parse.
    :param valid_class_codes: List of valid class codes to filter classes.
    :return: Dictionary with class names as keys and lists of student dictionaries as values.
    """
    class_students = {}
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Find all class headings
    class_headings = soup.find_all('h3')
    for heading in class_headings:
        class_name_raw = heading.get_text(strip=True)

        # Improved pattern to handle more variations
        pattern = r'\b(' + '|'.join(valid_class_codes) + r')-\d{3}(?:-\d+)?(?:-\w+)?\b'
        match = re.search(pattern, class_name_raw)
        if match:
            class_name = match.group(0)
        else:
            continue  # Skip if no valid class code is found

        # Get the next sibling, which should be the table of students
        table = heading.find_next_sibling('table')
        if table:
            students = []
            # Now extract students from the table
            table_cells = table.find_all('td', {'width': '180px'})
            for cell in table_cells:
                student = {}
                # Extract the image URL
                img_tag = cell.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    student['photo_url'] = img_tag['src']
                else:
                    # Attempt to generate a photo URL
                    # Note: We'll fill in the name and email first
                    text_parts = cell.get_text(separator='|').split('|')
                    if len(text_parts) >= 1:
                        student['name'] = text_parts[0].strip()
                    if len(text_parts) >= 2:
                        student['student_id'] = text_parts[1].strip()
                    if len(text_parts) >= 3:
                        student['email'] = text_parts[2].strip()
                    student['photo_url'] = generate_photo_url(student.get('name'), student.get('email'))

                # Extract student details
                text_parts = cell.get_text(separator='|').split('|')
                if len(text_parts) >= 1:
                    student['name'] = text_parts[0].strip()
                    student['student_id'] = text_parts[1].strip() if len(text_parts) > 1 else None
                    student['email'] = text_parts[2].strip() if len(text_parts) > 2 else None
                    students.append(student)
                else:
                    # Log or handle cells with no text data
                    logging.warning(f"No student data found in class {class_name}: {cell}")

            # Add students to the class in the dictionary
            if class_name not in class_students:
                class_students[class_name] = []
            class_students[class_name].extend(students)

    return class_students

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
        logging.error(f"Error validating URL '{url}': {e}")
        return False

def generate_photo_url(student_name, email=None):
    """
    Generate the photo URL based on the student's name and handle duplicates by appending numbers.

    :param student_name: Full name of the student.
    :param email: Email address of the student (optional).
    :return: Generated photo URL or None if not found.
    """
    if not student_name:
        return None
    try:
        name_parts = student_name.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0].lower()
            last_name = ''.join(name_parts[1:]).lower()
            first_initial = first_name[0]
            base_filename = f"{last_name}{first_initial}"
            base_url = f"https://directoryphotos.uindy.edu/{base_filename}"

            # First, try the base URL without any number
            if is_valid_url(base_url):
                return base_url

            # If not found, try appending numbers from 1 to 5
            for i in range(1, 6):
                photo_url_candidate = f"{base_url}{i}"
                if is_valid_url(photo_url_candidate):
                    return photo_url_candidate

        if email:
            email_username = email.split('@')[0]
            photo_url_candidate = f"https://directoryphotos.uindy.edu/{email_username}"
            if is_valid_url(photo_url_candidate):
                return photo_url_candidate

        return None
    except Exception as e:
        logging.error(f"Error generating photo URL for '{student_name}': {e}")
        return None
