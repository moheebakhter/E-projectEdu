import requests
from bs4 import BeautifulSoup

def scrape_propakistani_blogs():
    url = "https://propakistani.pk/category/others/education/"
    response = requests.get(url)
    blogs = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all article elements
        articles = soup.find_all('article')

        for article in articles:
            # Try different structures (some may not have h2.post-title)
            title_tag = article.find('h2') or article.find('h3') or article.find('a')
            link_tag = article.find('a')

            if title_tag and link_tag and link_tag.get('href'):
                title = title_tag.get_text(strip=True)
                link = link_tag['href']
                blogs.append({'title': title, 'link': link})

        # If nothing found, return fallback message
        if not blogs:
            blogs.append({'title': 'No blogs found — site layout may have changed.', 'link': '#'})

    else:
        blogs.append({'title': f'Failed to fetch page (status code {response.status_code})', 'link': '#'})

    return blogs