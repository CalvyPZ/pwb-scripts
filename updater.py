import pywikibot
import re
import os
from tqdm import tqdm
import time
import csv
import queue
from concurrent.futures import ThreadPoolExecutor

SORT_ORDER = [
    "|name", "|model", "|icon", "|icon_name",
    "|model2", "|icon2", "|icon_name2",
    "|model3", "|icon3", "|icon_name3",
    "|model4", "|icon4", "|icon_name4",
    "|model5", "|icon5", "|icon_name5",
    "|model6", "|icon6", "|icon_name6",
    "|model7", "|icon7", "|icon_name7",
    "|model8", "|icon8", "|icon_name8",
    "|model9", "|icon9", "|icon_name9",
    "|model10", "|icon10", "|icon_name10",
    "|model11", "|icon11", "|icon_name11",
    "|model12", "|icon12", "|icon_name12",
    "|model13", "|icon13", "|icon_name13",
    "|model14", "|icon14", "|icon_name14",
    "|model15", "|icon15", "|icon_name15",
    "|model16", "|icon16", "|icon_name16",
    "|model17", "|icon17", "|icon_name17",
    "|model18", "|icon18", "|icon_name18",
    "|model19", "|icon19", "|icon_name19",
    "|model20", "|icon20", "|icon_name20",
    "|model21", "|icon21", "|icon_name21",
    "|media_title",
    "|category", "|weight", "|weight_full", "|weight_reduction", "|max_units",
    "|equipped", "|attachment_type", "|function", "|primary_use", "|weapon1", "|weapon2", "|weapon3", "|weapon4",
    "|weapon5", "|weapon6", "|weapon7", "|weapon8", "|weapon9", "|part_type", "|skill_type", "|ammo_type", "|clip_size",
    "|material", "|material_value", "|contents",
    "|can_boil_water", "|consumed", "|writable", "|recipes", "|page_number", "|vol_number", "|packaged", "|rain_factor",
    "|days_fresh", "|days_rotten",
    "|cant_be_frozen", "|condition_max", "|condition_lower_chance", "|run_speed", "|combat_speed", "|scratch_defense",
    "|bite_defense", "|bullet_defense",
    "|neck_protection", "|insulation", "|wind_resistance", "|water_resistance", "|light_distance", "|light_strength",
    "|torch_cone", "|wet_cooldown", "|sensor_range",
    "|energy_source", "|two_way", "|mic_range", "|transmit_range", "|min_channel", "|max_channel", "|damage_type",
    "|min_damage", "|max_damage", "|door_damage",
    "|tree_damage", "|min_range", "|max_range", "|min_range_mod", "|max_range_mod", "|hit_chance", "|recoil_delay",
    "|sound_radius", "|base_speed", "|swing_time", "|push_back", "|knockdown",
    "|aiming_time", "|aiming_mod", "|reload_time", "|crit_chance", "|crit_multiplier", "|angle_mod", "|kill_move",
    "|weight_mod", "|reload_mod",
    "|aiming_change", "|reloading_change", "|effect_type", "|type", "|effect_power", "|effect_range",
    "|effect_duration", "|effect_timer", "|hunger_change", "|thirst_change", "|calories", "|carbohydrates", "|proteins",
    "|lipids", "|unhappy_change", "|boredom_change",
    "|stress_change", "|panic_change", "|fatigue_change", "|endurance_change", "|flu_change", "|pain_change",
    "|sick_change", "|alcoholic", "|alcohol_power",
    "|reduce_infection_power", "|bandage_power", "|poison_power", "|cook_minutes", "|burn_minutes",
    "|dangerous_uncooked", "|bad_microwaved", "|good_hot", "|bad_cold",
    "|spice", "|evolved_recipe", "|workstation", "|tool", "|ingredients", "|tag", "|tag2", "|tag3", "|tag4", "|tag5",
    "|capacity", "|item_id", "|guid",
    "|itemdisplayname", "|recmedia"
]


def update_distro(page, article_name):
    skip_headers = [
        "{{Header|Project Zomboid|World|Lore|Media|CDs}}",
        "{{Header|Project Zomboid|World|Lore|Media|VHS tapes|Home VHS}}",
        "{{Header|Project Zomboid|World|Lore|Media|VHS tapes|Retail VHS}}"
    ]
    original_text = page.text

    if any(header in original_text for header in skip_headers):
        return original_text, False

    new_text = original_text
    has_edited = False

    pattern = r"<!--BOT FLAG\|([^|]+)\|([^|]+)-->(.*?)<!--END BOT FLAG\|\1\|\2-->"
    matches = list(re.finditer(pattern, new_text, flags=re.DOTALL))
    for match in matches:
        flag_key, flag_id, content_between = match.groups()
        file_path = os.path.join(r"C:\Users\Calvy\Downloads\CodeProjects\pz-distribution-to-wikitable\output\complete", f"{flag_key}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as content_file:
                replacement_content = content_file.read()
                new_text = new_text.replace(match.group(0), replacement_content)
                has_edited = True

    return new_text, has_edited


def sort_infobox(infobox):
    def key_sort(line):
        key = line.split('=')[0].strip()
        if key in SORT_ORDER:
            return SORT_ORDER.index(key)
        return len(SORT_ORDER)  # Assign a default large value to keys not in SORT_ORDER

    infobox_lines = infobox.split('\n')[1:-1]  # Exclude the first '{{Infobox item' and the last '}}'
    sorted_infobox_lines = sorted(infobox_lines, key=key_sort)

    # Reconstruct the infobox
    sorted_infobox = '{{Infobox item\n' + '\n'.join(sorted_infobox_lines) + '\n}}'
    return sorted_infobox


def process_infobox(page, infobox, article_name):
    infobox_lines = infobox.split('\n')
    item_id_line = next((line for line in infobox_lines if '|item_id=' in line), None)
    item_id2_line = next((line for line in infobox_lines if '|item_id2=' in line), None)

    if item_id2_line or (item_id_line and '<br>' in item_id_line):
        with open('double_items.txt', 'a', encoding='utf-8') as double_items:
            double_items.write(f"{article_name}\n")
        return None, False

    item_id = re.search(r'\|item_id=(.*)', item_id_line).group(1).strip() if item_id_line else None

    if item_id is None:
        with open('no_infobox_file.txt', 'a', encoding='utf-8') as no_infobox_file:
            no_infobox_file.write(f"{article_name}\n")
        return None, False

    dir_path = r'C:\Users\Calvy\Downloads\CodeProjects\pz-script_parser\output\infoboxes'
    matched_file = None

    for root, _, files in os.walk(dir_path):
        for file in files:
            if item_id and file.startswith(item_id):
                matched_file = os.path.join(root, file)
                break
        if matched_file:
            break

    if matched_file:
        with open(matched_file, 'r', encoding='utf-8') as f:
            new_infobox = f.read().strip().split('\n')

        new_infobox_dict = {line.split('=')[0].strip(): line.split('=')[1].strip() for line in new_infobox if '=' in line}
        infobox_dict = {line.split('=')[0].strip(): line.split('=')[1].strip() for line in infobox_lines if '=' in line}

        edit_made = False

        for key, value in new_infobox_dict.items():
            if key.startswith('|model') and key not in infobox_dict:
                continue
            if key.startswith(('|name', '|model', '|icon', '|icon_name', '|category', '|material', '|weapon',
                               '|weapons', '|skill_type', '|ammo_type', '|recipes', '|tag', '|evolved_recipe')):
                continue
            if key not in infobox_dict or infobox_dict[key] != value:
                infobox_dict[key] = value
                edit_made = True

        for key, value in new_infobox_dict.items():
            if key not in infobox_dict and not key.startswith('|model'):
                infobox_dict[key] = value
                edit_made = True

        updated_infobox = '{{Infobox item\n'
        for key, value in infobox_dict.items():
            updated_infobox += f'{key}={value}\n'
        updated_infobox += '}}'

        sorted_infobox = sort_infobox(updated_infobox)
        if sorted_infobox != infobox:
            page.text = page.text.replace(infobox, sorted_infobox)
        return sorted_infobox, edit_made
    else:
        sorted_infobox = sort_infobox(infobox)
        if sorted_infobox != infobox:
            page.text = page.text.replace(infobox, sorted_infobox)
        return sorted_infobox, False


def sanitize_filename(filename):

    return re.sub(r'[^A-Za-z0-9_.-]', '_', filename)


def process_codebox(page, article_name):
    text = page.text
    pattern = re.compile(r'{{CodeSnip(.*?)}}', re.DOTALL)
    updated = False

    for match in re.finditer(pattern, text):
        snippet = match.group(0)
        item_name_pattern = re.compile(r'\|\s*code\s*=\s*\n(.*?)\n', re.DOTALL)
        item_name_match = item_name_pattern.search(snippet)
        if item_name_match:
            item_name = item_name_match.group(1).strip().replace("item ", "")
            sanitized_item_name = sanitize_filename(item_name)
            try:
                with open(f'./output/{sanitized_item_name}.txt', 'r') as f:
                    new_snippet = f.read()
                    if new_snippet != snippet:  # Check if snippet has changed
                        text = text.replace(snippet, new_snippet)
                        updated = True
            except FileNotFoundError:
                with open('failed_code.csv', 'a', newline='') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([article_name, f"Item file not found: {sanitized_item_name}.txt"])
        else:
            with open('failed_code.csv', 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow([article_name, "Item name not found in CodeSnip"])

    return text, updated


def formatting(text):
    lines = text.split('\n')
    made_changes = False
    i = 0
    in_codebox_section = False

    while i < len(lines):
        line = lines[i]

        if line.startswith('{{Codebox'):
            in_codebox_section = True

        if in_codebox_section and line.startswith('==See also=='):
            in_codebox_section = False

        if in_codebox_section:
            i += 1
            continue

        original_line = lines[i]
        cleaned_line = original_line.rstrip()
        lines[i] = cleaned_line

        if cleaned_line != original_line:
            made_changes = True

        if line.startswith('{{Infobox'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('}}'):
                j += 1
            if j < len(lines) and lines[j].startswith('}}'):
                k = j + 1
                while k < len(lines) and lines[k].strip() == '':
                    lines.pop(k)
                    made_changes = True
            i = j + 1
            continue

        if line.startswith('==') and not line.startswith('==='):
            if i > 0 and lines[i - 1].strip():
                lines.insert(i, '')
                made_changes = True
                i += 1

            if i + 1 < len(lines):
                j = i + 1
                while j < len(lines) and lines[j].strip() == '':
                    lines.pop(j)
                    made_changes = True
                i = j - 1

        elif line.startswith('===') and not line.startswith('===='):
            if i > 0:
                prev_line = lines[i - 1].strip()

                if prev_line.startswith('==') and not prev_line.startswith('==='):
                    i += 1
                    continue

                elif prev_line == '':
                    if i > 1 and not lines[i - 2].strip():
                        lines.pop(i - 1)
                        made_changes = True
                        i -= 1

                elif not prev_line.startswith('=='):
                    lines.insert(i, '')
                    made_changes = True
                    i += 1

        if line.startswith('{{Navbox'):
            if i > 0 and lines[i - 1].strip():
                lines.insert(i, '')
                made_changes = True
                i += 1

            if i + 1 < len(lines) and lines[i + 1].strip():
                lines.insert(i + 1, '')
                made_changes = True

        i += 1

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
        return '\n'.join(cleaned_lines)
    return text


def check_and_queue(article_name, version, site, q):
    # Read the blacklist once and store it in a set
    with open('infobox_blacklist.txt', 'r', encoding='utf-8') as f:
        blacklist = set(line.strip() for line in f)

    if article_name in blacklist:
        return

    page = pywikibot.Page(site, article_name)

    if not page.exists():
        return

    original_text = page.text
    text, distro_updated = update_distro(page, article_name)  # Update distro before formatting

    if distro_updated:
        page.text = text  # Update the page text with the changes from update_distro

    infobox_match = re.search(r'(\{\{Infobox item.*?\n)(.*?\n)*?(\}\})', text, re.DOTALL)

    if not infobox_match:
        return

    infobox = infobox_match.group()

    sorted_infobox, infobox_updated = process_infobox(page, infobox, article_name)
    updated_text, codebox_updated = process_codebox(page, article_name)

    updated_text = formatting(updated_text)

    if original_text != updated_text:  # Compare original text with updated text
        q.put((article_name, updated_text))


def process_infobox_and_codebox(article_name, updated_text, site):
    page = pywikibot.Page(site, article_name)
    page.text = updated_text
    try:
        page.save(summary="Automated Infobox, distribution, code, and formatting.", minor=True, tags="bot")
        time.sleep(8)  # Rate limit after saving page
    except Exception as e:
        pass


def main():
    version = "41.78.16"
    site = pywikibot.Site()
    site.login()

    with open('search_results.txt', 'r', encoding='utf-8') as f:
        articles = f.readlines()

    q = queue.Queue()

    with ThreadPoolExecutor(max_workers=75) as executor:
        futures = [executor.submit(check_and_queue, article_name.strip(), version, site, q) for article_name in articles]
        for future in tqdm(futures, desc="Queueing articles"):
            future.result()

    queued_articles = []
    while not q.empty():
        queued_articles.append(q.get())

    queued_articles.sort(key=lambda x: x[0])  # Sort alphabetically by article name

    for article_name, updated_text in tqdm(queued_articles, desc="Processing queue"):
        process_infobox_and_codebox(article_name, updated_text, site)


if __name__ == "__main__":
    main()
