import pywikibot
import time
from tqdm import tqdm

def resolve_redirect(site, title):
    """Resolve the final target of a redirect."""
    page = pywikibot.Page(site, title)
    while page.isRedirectPage():
        page = page.getRedirectTarget()
    return page.title()

def main():
    site = pywikibot.Site()
    site.login()  # Login with no parameters

    # Get double redirects using the API
    double_redirects = []
    req = site.simple_request(action='query', list='querypage', qppage='DoubleRedirects', qplimit='max')
    data = req.submit()

    if 'query' in data:
        double_redirects.extend(data['query']['querypage']['results'])

    # Use tqdm for a progress bar
    for page_data in tqdm(double_redirects, desc="Processing double redirects"):
        page = pywikibot.Page(site, page_data['title'])
        if page.isRedirectPage():
            final_target = resolve_redirect(site, page.title())

            # Check if the redirect needs to be updated
            if page.getRedirectTarget().title() != final_target:
                # Update the redirect to point directly to the final target
                page.text = f"#REDIRECT [[{final_target}]]"
                page.save(summary=f"Fixing double redirect to point directly to [[{final_target}]]")
                time.sleep(6)  # Rate limit

if __name__ == "__main__":
    main()
