# html_parse.py

from bs4 import BeautifulSoup
from utils import is_valid_url, log_message

def parse_html_file(html_file):
    """
    Parse the HTML file and extract student information, grouped by class.

    :param html_file: Path to the HTML file.
    :return: Dictionary with class names as keys and lists of student dictionaries as values.
    """
    class_students = {}
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Find all class headings
    class_headings = soup.find_all('h3')
    for heading in class_headings:
        class_name_raw = heading.get_text(strip=True)
        # Extract the class code from the raw class name
        class_code = class_name_raw.split()[1]  # Assumes class code is the second word
        class_code = class_code.strip()

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
                    photo_url = img_tag['src']
                    # Validate the photo URL
                    if is_valid_url(photo_url):
                        student['photo_url'] = photo_url
                    else:
                        student['photo_url'] = None
                else:
                    student['photo_url'] = None

                # Extract text elements
                text_parts = cell.get_text(separator='|').split('|')
                if len(text_parts) >= 3:
                    student['name'] = text_parts[0].strip()
                    student['student_id'] = text_parts[1].strip()
                    student['email'] = text_parts[2].strip()
                    # Exclude the major field
                else:
                    continue  # Skip if data is incomplete

                # If photo_url is not available, generate it
                if not student.get('photo_url'):
                    student['photo_url'] = generate_photo_url(student['name'], student['email'])

                students.append(student)

            # Add the students to the class in the dictionary
            class_students[class_code] = students

    return class_students

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

            # Optionally, try using the email username if available
            if email:
                email_username = email.split('@')[0]
                photo_url_candidate = f"https://directoryphotos.uindy.edu/{email_username}"
                if is_valid_url(photo_url_candidate):
                    return photo_url_candidate

            # If none of the patterns result in a valid URL, return None
            return None
        else:
            return None
    except Exception as e:
        log_message(f"Error generating photo URL for {student_name}: {e}", "error")
        return None
