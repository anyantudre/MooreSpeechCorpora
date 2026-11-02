import re


### function to sanitize file names (in case it's needed)
def sanitize_filename(filename):
    """Sanitize the filename by replacing spaces and removing special characters.

    Args:
        filename (str): The original filename.

    Returns:
        str: A sanitized version of the filename.
    """
    sanitized_filename = re.sub(r'[éè]', 'e', filename)
    sanitized_filename = re.sub(r'[à]', 'a', filename)
    # Replace spaces with underscores and remove special characters
    sanitized_filename = re.sub(r'[^A-Za-z0-9_.-]', '_', filename)
    return sanitized_filename