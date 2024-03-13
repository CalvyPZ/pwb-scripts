import pywikibot
from tqdm import tqdm
import time

def find_and_replace(site, page_title, mappings):
    try:
        page = pywikibot.Page(site, page_title)
        if not page.exists():
            print(f"Page {page_title} does not exist.")
            return

        text = page.text
        original_text = text[:]

        for phrase, replacement in mappings.items():
            text = text.replace(phrase, replacement)

        if text != original_text:
            page.text = text
            page.save(summary="Automated linking update", minor=True)
            time.sleep(10)
        else:
            print(f"No changes made to {page_title}.")

    except Exception as e:
        print(f"An error occurred while processing {page_title}: {e}")

def main():
    site = pywikibot.Site()
    site.login()

    mappings = {
        'find': 'replace',
    }

    try:
        with open("search_results.txt", "r", encoding='utf-8') as file:
            pages = file.readlines()
            pages = [page.strip() for page in pages]

        for page_title in tqdm(pages, desc="Processing pages"):
            find_and_replace(site, page_title, mappings)

    except FileNotFoundError:
        print("search_results.txt file not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
