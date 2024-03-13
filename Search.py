import os
import datetime
import pywikibot
from pywikibot import pagegenerators
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import re
from tqdm import tqdm


def file_updated_within_last_48_hours(filepath):
    last_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
    current_time = datetime.datetime.now()
    difference = current_time - last_modified_time
    return difference.total_seconds() < (48 * 3600)


def check_and_prepare_page_list(site):
    filepath = 'wiki_directory.txt'
    if os.path.exists(filepath) and file_updated_within_last_48_hours(filepath):
        print(f"{filepath} exists and was updated within the last 48 hours.")
    else:
        print(f"{filepath} does not exist or was not updated within the last 48 hours. Fetching all pages...")
        fetch_and_write_page_titles(site, filepath)

def fetch_and_write_page_titles(site, filepath):
    exclude_namespaces = [-2, -1, 2, 3, 6, 7, 8, 9]
    with open(filepath, 'w', encoding='utf-8') as file, tqdm(desc="Fetching all page titles", unit='pages') as pbar:
        for ns_id, ns_info in site.namespaces.items():
            if ns_id in exclude_namespaces:
                continue
            for page in site.allpages(namespace=ns_id, total=None, filterredir=False):
                file.write(f"{page.title()}\n")
                pbar.update(1)


def search_by_title(site, search_term, include_categories=False):
    gen = pagegenerators.AllpagesPageGenerator(site=site, total=None)
    matching_titles = []

    for page in gen:
        if search_term.lower() in page.title().lower():
            if include_categories or not page.title().startswith("Category:"):
                matching_titles.append(page.title())

    # Write matching titles to file
    with open("search_results.txt", "a", encoding='utf-8') as file:
        for title in matching_titles:
            file.write(f"{title}\n")


def search_by_category(site, category_name, include_subcategories):
    with open("search_results.txt", "a", encoding='utf-8') as file:
        cat = pywikibot.Category(site, category_name)
        pages = cat.articles(recurse=include_subcategories)  # Recurse if include_subcategories is True
        for page in pages:
            if not page.title().startswith("Category:"):
                file.write(f"{page.title()}\n")



def search_page_body(page, search_terms, case_sensitive, ignore_country_codes, ignore_string, include_categories,
                     progress_bar=None):
    # Regex to match country codes or specific language variants at the end of a page title
    country_code_pattern = re.compile(r"/([a-z]{2}|pt-br|zh-hans|zh-hant)$", re.IGNORECASE)
    if ignore_country_codes and country_code_pattern.search(page.title()):
        return None
    if page.namespace() == 14 and not include_categories:
        return None

    text = page.text
    # Ignore the page if it contains the ignore string
    if ignore_string and ignore_string in text:
        return None

    # Initialize the progress bar if provided
    if progress_bar:
        progress_bar.update(1)

    # Search for each term in the text
    for term in search_terms:
        if (case_sensitive and term in text) or (not case_sensitive and term.lower() in text.lower()):
            return page.title()
    return None


def search_in_body(site, search_terms, case_sensitive, ignore_string, include_categories):
    with open("wiki_directory.txt", "r", encoding='utf-8') as file, open("search_results.txt", "a", encoding='utf-8') as out_file:
        pages_to_search = [pywikibot.Page(site, title.strip()) for title in file]
        num_pages = len(pages_to_search)

        def process_page(page):
            try:
                if not include_categories and page.namespace() == 14:
                    return None  # Skip category pages if not included
                text_lines = page.text.split('\n')
                for line in text_lines:
                    if case_sensitive:
                        if any(term in line for term in search_terms):
                            return page.title()
                    else:
                        if any(term.lower() in line.lower() for term in search_terms):
                            return page.title()
                return None
            except Exception as e:
                print(f"Error processing page {page.title()}: {e}")
                return None

        with tqdm(total=num_pages, desc="Searching pages") as pbar:

            with ThreadPoolExecutor(max_workers=6) as executor:
                future_to_page = {executor.submit(process_page, page): page for page in pages_to_search}
                for future in concurrent.futures.as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        result = future.result()
                        if result:
                            out_file.write(f"{result}\n")
                    except Exception as e:
                        print(f"Error processing page {page.title()}: {e}")
                    pbar.update(1)


def login_to_site():
    try:
        site = pywikibot.Site()
        site.login()
        return site
    except pywikibot.exceptions.NoUsername:
        print("Error: No username configured for this site.")
        return None


def main():
    site = login_to_site()
    if site:
        check_and_prepare_page_list(site)

        # Clear the search_results.txt file before starting any new search
        open("search_results.txt", "w").close()

        print("Select the type of search you want to perform:")
        print("1. Page Title")
        print("2. Category")
        print("3. Body")
        search_choice = input("Enter your choice (1/2/3): ")

        ignore_country_codes = input("Ignore language pages? (Y/N): ").upper() == 'Y'

        search_type = {"1": "title", "2": "category", "3": "body"}.get(search_choice)

        if search_type == "title":
            include_categories = input("Include categories in the search results? (Y/N): ").upper() == 'Y'
            search_term = input("Enter the title to search for: ")
            search_by_title(site, search_term, include_categories)
        elif search_type == "category":
            category_name = input("Enter the category name: ")
            include_subcategories = input("Include subcategories? (Y/N): ").upper() == 'Y'
            search_by_category(site, category_name, include_subcategories)
        if search_type == "body":
            include_categories = input("Include categories in the search results? (Y/N): ").upper() == 'Y'
            search_terms_input = input("Enter the texts to search for in the body, separated by commas: ")
            search_terms = [term.strip() for term in search_terms_input.split(',')]
            case_sensitive = input("Case sensitive search? (Y/N): ").upper() == 'Y'
            ignore_string = input("Enter a string to ignore in pages (leave blank to ignore none): ")
            search_in_body(site, search_terms, case_sensitive, ignore_string, include_categories)

if __name__ == "__main__":
    main()
