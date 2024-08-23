import pywikibot
import time
from tqdm import tqdm
import concurrent.futures
import queue

# Configure your site (e.g., 'en', 'wikipedia')
site = pywikibot.Site()
site.login()


def process_page(page):
    text = page.text
    lines = text.split('\n')
    made_changes = False
    i = 0
    in_codebox_section = False

    while i < len(lines):
        line = lines[i]

        # Detect start of Codebox section
        if line.startswith('{{Codebox'):
            in_codebox_section = True

        # Detect end of Codebox section
        if in_codebox_section and line.startswith('==See also=='):
            in_codebox_section = False

        # If in Codebox section, skip processing
        if in_codebox_section:
            i += 1
            continue

        # Remove trailing whitespaces from the end of each line
        original_line = lines[i]
        cleaned_line = original_line.rstrip()
        lines[i] = cleaned_line

        # Check if this operation actually changed the line
        if cleaned_line != original_line:
            made_changes = True

        # Check for Infobox start
        if line.startswith('{{Infobox'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('}}'):
                j += 1
            if j < len(lines) and lines[j].startswith('}}'):
                # Remove empty lines immediately after '}}' until a non-empty line is found
                k = j + 1
                while k < len(lines) and lines[k].strip() == '':
                    lines.pop(k)  # Do not increment k, since pop shifts subsequent items left
                    made_changes = True
            i = j + 1  # Move index past the Infobox section
            continue

        # Check for second-level section header (== Header ==)
        if line.startswith('==') and not line.startswith('==='):
            # Ensure there is a blank line before the header if there isn't one already
            if i > 0 and lines[i - 1].strip():
                lines.insert(i, '')
                made_changes = True
                i += 1  # Adjust index for inserted line

            # Ensure the line following the header is not empty
            if i + 1 < len(lines):
                j = i + 1
                while j < len(lines) and lines[j].strip() == '':
                    lines.pop(j)  # Remove the empty line
                    made_changes = True
                i = j - 1  # Adjust index to point to the header line

        # Check for third-level section header (=== Subheader ===)
        elif line.startswith('===') and not line.startswith('===='):
            if i > 0:
                prev_line = lines[i - 1].strip()

                # If the line above starts with ==, do nothing
                if prev_line.startswith('==') and not prev_line.startswith('==='):
                    i += 1
                    continue

                # If the line above is empty, check the line above it
                elif prev_line == '':
                    if i > 1 and not lines[i - 2].strip():
                        # Remove one of the empty lines if the one above the empty line is also empty
                        lines.pop(i - 1)
                        made_changes = True
                        i -= 1  # Adjust index for removed line

                # If the line above has text but does not start with ==, insert an empty line
                elif not prev_line.startswith('=='):
                    lines.insert(i, '')
                    made_changes = True
                    i += 1  # Adjust index for inserted line

        # Check for Navbox
        if line.startswith('{{Navbox'):
            # Ensure there is a blank line before the Navbox if there isn't one already
            if i > 0 and lines[i - 1].strip():
                lines.insert(i, '')
                made_changes = True
                i += 1  # Adjust index for inserted line

            # Ensure there is a blank line after the Navbox if there isn't one already
            if i + 1 < len(lines) and lines[i + 1].strip():
                lines.insert(i + 1, '')
                made_changes = True

        i += 1  # Normal increment of i

    # Remove double empty lines
    cleaned_lines = []
    previous_line_empty = False
    for line in lines:
        if line.strip() == '':
            if not previous_line_empty:
                cleaned_lines.append(line)
                previous_line_empty = True
            else:
                made_changes = True
        else:
            cleaned_lines.append(line)
            previous_line_empty = False

    if made_changes:
        page.text = '\n'.join(cleaned_lines)
        return True
    return False


def check_page(title, change_queue):
    page = pywikibot.Page(site, title)
    original_text = page.text
    if process_page(page) and page.text != original_text:
        change_queue.put(title)


def main():
    with open('wiki_directory.txt', 'r', encoding='utf-8') as file:
        titles = file.read().splitlines()

    # Thread-safe queue for pages that need changes
    change_queue = queue.Queue()

    # Multithreaded check with tqdm progress bar
    with concurrent.futures.ThreadPoolExecutor(max_workers=75) as executor:
        futures = {executor.submit(check_page, title, change_queue): title for title in titles if title}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Checking pages"):
            future.result()  # Ensure any exceptions are raised

    # Convert queue to a list and sort alphabetically
    pages_to_process = sorted(list(change_queue.queue))

    # Single-threaded processing with rate limiting
    for title in tqdm(pages_to_process, desc="Processing pages"):
        page = pywikibot.Page(site, title)
        if process_page(page):
            try:
                # Save the page with a summary
                page.save(summary="Automated Formatting", tags="bot")
                time.sleep(7)  # Adhere to rate limiting
            except pywikibot.exceptions.Error as e:
                print(f"Error saving page '{title}': {e}")

if __name__ == "__main__":
    main()
