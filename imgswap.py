import pywikibot
from tqdm import tqdm
import time

# Mapping of files to be replaced
item_mapping = {
        "File:REPLACED.png": "File:REPLACER.png",
}


def replace_file_usage_and_mark_deletion(site, old_file, new_file):
    old_file_name = old_file.replace('File:', '')
    new_file_name = new_file.replace('File:', '')

    file_page = pywikibot.FilePage(site, old_file)
    using_pages = list(file_page.using_pages())

    for page in using_pages:
        text = page.text
        text2 = text
        # Check and replace all files in the mapping
        for ofn, nfn in item_mapping.items():
            ofn = ofn.replace('File:', '')
            nfn = nfn.replace('File:', '')
            text = text.replace(ofn, nfn)

        if text2 != text:
            page.text = text
            page.save(summary="Automatic file swap", minor=True, tags="bot")
            time.sleep(6)
        else:
            pass

    # After all uses are replaced, check if the file is no longer in use and mark for deletion
    old_file_page = pywikibot.FilePage(site, old_file)
    if not list(old_file_page.using_pages(total=1)):
        # Check if the deletion template is already in the page text
        if "{{Delet" not in old_file_page.text:
            delete_notice = f"{{{{Delete|Duplicate, replaced by [[:{new_file}]]}}}}\n"
            old_file_page.text = delete_notice + old_file_page.text
            old_file_page.save(summary="Marking duplicate file for deletion", minor=True, tags="bot")
            time.sleep(6)


def main():
    site = pywikibot.Site()
    site.login()

    # Iterate through each file replacement with a tqdm progress bar
    for old_file, new_file in tqdm(item_mapping.items(), desc="Processing files and marking for deletion",
                                   total=len(item_mapping)):
        replace_file_usage_and_mark_deletion(site, old_file, new_file)


if __name__ == "__main__":
    main()