import os
import datetime
import pywikibot
import concurrent.futures
import re
from tqdm import tqdm
import time


def file_updated_within_last_48_hours(filepath):
    last_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
    current_time = datetime.datetime.now()
    difference = current_time - last_modified_time
    return difference.total_seconds() < (24 * 3600)


def check_and_prepare_page_list(site):
    filepath = 'wiki_directory.txt'
    if not (os.path.exists(filepath) and file_updated_within_last_48_hours(filepath)):
        #exclude_namespaces = [-2, -1]
        exclude_namespaces = [-2, -1, 2, 3, 6, 7, 8, 9]
        with open(filepath, 'w', encoding='utf-8') as file:
            for ns_id, ns_info in site.namespaces.items():
                if ns_id in exclude_namespaces:
                    continue
                for page in site.allpages(namespace=ns_id, total=None, filterredir=False):
                    file.write(f"{page.title()}\n")


def clear_search_results():
    with open("search_results.txt", "w", encoding='utf-8') as file:
        file.truncate()


def read_lines(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file]


def write_lines(filepath, lines):
    with open(filepath, 'w', encoding='utf-8') as file:
        file.writelines(f"{line}\n" for line in lines)


def process_page(title, site, search_terms, case_sensitive, ignore_string, ignore_country_codes, country_code_pattern,
                 search_terms_lower):
    page = pywikibot.Page(site, title)
    if page.namespace() != 0:  # Skip non-main namespaces
        return None
    if ignore_country_codes and country_code_pattern.search(page.title()):
        return None
    page_text = page.text
    if ignore_string:
        if case_sensitive and ignore_string in page_text:
            return None
        elif not case_sensitive and ignore_string.lower() in page_text.lower():
            return None

    if case_sensitive:
        if any(term in page_text for term in search_terms):
            return page.title()
    else:
        page_text_lower = page_text.lower()
        if any(term in page_text_lower for term in search_terms_lower):
            return page.title()

    return None


def search_in_body(site, search_terms, case_sensitive, ignore_string, ignore_country_codes, max_threads=80):
    clear_search_results()
    pages_to_search = read_lines("wiki_directory.txt")

    search_terms_lower = [term.lower() for term in search_terms]
    country_code_pattern = re.compile(r"/([a-z]{2}|pt-br|zh-hans|zh-hant)$", re.IGNORECASE)

    batch_results = []
    progress_bar = tqdm(total=len(pages_to_search), desc="Processing pages")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(
                process_page, title, site, search_terms, case_sensitive, ignore_string, ignore_country_codes,
                country_code_pattern, search_terms_lower
            ) for title in pages_to_search
        ]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                batch_results.append(result)
            progress_bar.update(1)

    progress_bar.close()

    batch_results.sort()
    write_lines("search_results.txt", batch_results)


def login_to_site():
    retry_attempts = 5
    retry_delay = 3
    for attempt in range(retry_attempts):
        try:
            site = pywikibot.Site()
            site.login()
            return site
        except pywikibot.exceptions.ServerError as e:
            print(f"Server error encountered: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    print("Failed to login after multiple attempts.")
    return None


def get_user_input(prompt, valid_responses=None, default=None):
    while True:
        response = input(prompt).strip()
        if not response and default is not None:
            return default
        if valid_responses and response.upper() not in valid_responses:
            print(f"Invalid response. Please choose from {valid_responses}.")
        else:
            return response.upper() if valid_responses else response


def main():
    site = login_to_site()
    if not site:
        return

    check_and_prepare_page_list(site)

    search_terms_input = get_user_input("Enter the texts to search for in the body, separated by commas: ")
    search_terms = [term.strip() for term in search_terms_input.split(',')]
    ignore_string = get_user_input("Enter a string to ignore in pages (leave blank to ignore none): ")
    ignore_country_codes = get_user_input("Ignore language pages? (Y/N) [default: Y]: ", {"Y", "N"}, default="Y") == 'Y'
    case_sensitive = get_user_input("Case sensitive search? (Y/N) [default: N]: ", {"Y", "N"}, default="N") == 'N'

    search_in_body(site, search_terms, case_sensitive, ignore_string, ignore_country_codes)


if __name__ == "__main__":
    main()
