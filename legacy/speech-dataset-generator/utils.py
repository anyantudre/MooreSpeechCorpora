import re


### function to sanitize file names (in case it's needed)
def sanitize_filename(filename):
    """Sanitize the filename by replacing spaces and removing special characters.

    Args:
        filename (str): The original filename.

    Returns:
        str: A sanitized version of the filename.
    """
    # Replace spaces with underscores and remove special characters
    return re.sub(r'[^A-Za-z0-9_.-]', '_', filename)