import os
import re
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import pywikibot
from pywikibot import sleep


def count_items(files):
    count = 0
    for file_path in files:
        with open(file_path, 'r') as f:
            count += sum(1 for line in f if line.strip().startswith('item'))
    return count


def process_file(file_path, version, progress=None):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.strip().startswith('item'):
                item_code, line_num = extract_code_snippet(i, lines)
                item_name = line.split()[1]
                save_snippet(item_name, item_code, line_num, os.path.basename(file_path), version)
        if progress is not None:
            progress.update(1)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")


def code_base_main(version):
    if not os.path.exists('./output'):
        os.makedirs('./output')
    files = [os.path.join(root, file) for root, dirs, files in os.walk("./resources") for file in files]
    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = [executor.submit(process_file, file_path, version) for file_path in files]
        for future in as_completed(futures):
            pass


def extract_code_snippet(line_number, lines):
    item_code = ""
    for i in range(line_number, len(lines)):
        item_code += lines[i]
        if '}' in lines[i]:
            break
    return item_code, line_number + 1


def save_snippet(item_name, item_code, line, source, version):
    def write_snippet(name):
        formatted_code = f"""{{{{CodeSnip
  | lang = java
  | line = true
  | start = {line}
  | source = {source}
  | retrieved = true
  | version = {version}
  | code =
{item_code.strip()} 
}}}}"""
        with open(f'./output/{name}.txt', 'w') as f:
            f.write(formatted_code)

    write_snippet(item_name)
    if item_name.endswith("TEXTURE_TINT") or item_name.endswith("DECAL_TINT"):
        base_name = item_name.replace("TEXTURE_TINT", "").replace("DECAL_TINT", "")
        write_snippet(base_name)


def wiki_main(version):
    site = pywikibot.Site()
    site.login()
    search_results = [line.strip() for line in open('search_results.txt', 'r', encoding='utf-8')]
    progress = tqdm(total=len(search_results), desc="Updating wiki pages")

    for article_name in search_results:
        process_article(article_name, version, site)
        progress.update(1)


def process_article(article_name, version, site):
    page = pywikibot.Page(site, article_name)
    text = page.text
    pattern = re.compile(r'{{CodeSnip(.*?)}}', re.DOTALL)
    updated = False

    for match in re.finditer(pattern, text):
        snippet = match.group(0)
        item_name_pattern = re.compile(r'\|\s*code\s*=\s*\n(.*?)\n', re.DOTALL)
        item_name_match = item_name_pattern.search(snippet)
        if item_name_match:
            item_name = item_name_match.group(1).strip().replace("item ", "")
            try:
                with open(f'./output/{item_name}.txt', 'r') as f:
                    new_snippet = f.read()
                    if new_snippet != snippet:  # Check if snippet has changed
                        text = text.replace(snippet, new_snippet)
                        updated = True
            except FileNotFoundError:
                with open('failed_code.csv', 'a', newline='') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([article_name, "Item file not found"])
        else:
            with open('failed_code.csv', 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow([article_name, "Item name not found in CodeSnip"])

    if updated:
        page.text = text
        try:
            page.save(summary="Automated CodeBox update", tags="bot")
            sleep(6)
        except Exception as e:
            pass


if __name__ == "__main__":
    version = "41.78.16"
    while True:
        choice = input("Update code base (1) or update wiki (2)?: ")
        if choice == '1':
            code_base_main(version)
        elif choice == '2':
            wiki_main(version)
        elif choice == 'exit':
            break
        else:
            print("Invalid choice")
