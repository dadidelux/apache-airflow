import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_amazon_data_books(num_books=10):
    base_url = "https://www.amazon.com/s?k=data+engineering+books"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.amazon.com/"
    }

    books = []
    seen_titles = set()
    page = 1

    while len(books) < num_books:
        url = f"{base_url}&page={page}"
        response = requests.get(url, headers=headers, verify=False)
        print(f"Fetching: {url} [{response.status_code}]")
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            book_containers = soup.find_all("div", {"class": "s-result-item"})
            for book in book_containers:
                title = book.find("span", {"class": "a-text-normal"})
                author = book.find("a", {"class": "a-size-base"})
                price = book.find("span", {"class": "a-price-whole"})
                rating = book.find("span", {"class": "a-icon-alt"})
                if title and author and price and rating:
                    book_title = title.text.strip()
                    if book_title not in seen_titles:
                        seen_titles.add(book_title)
                        books.append({
                            "Title": book_title,
                            "Author": author.text.strip(),
                            "Price": price.text.strip(),
                            "Rating": rating.text.strip(),
                        })
            page += 1
        else:
            print("Failed to retrieve the page")
            break

    books = books[:num_books]
    df = pd.DataFrame(books)
    df.drop_duplicates(subset="Title", inplace=True)
    print(df)
    return df

if __name__ == "__main__":
    get_amazon_data_books(10)
