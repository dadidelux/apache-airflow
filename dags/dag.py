# task

# operators

# hooks

# dependencies

from datetime import datetime, timedelta
from airflow import DAG
import requests
import pandas as pd
from bs4 import BeautifulSoup
from airflow.operators.python import PythonOperator
# from airflow.providers.postgres.operators.postgres import PostgresOperator
# from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.mysql.hooks.mysql import MySqlHook

#1) fetch amazon data (extract) 2) clean data (transform)

def get_amazon_data_books(num_books, ti, max_pages=3):
    # Base URL of the Amazon search results for data science books
    base_url = f"https://www.amazon.com/s?k=data+engineering+books"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.amazon.com/"
    }

    books = []
    seen_titles = set()  # To keep track of seen titles
    page = 1

    while len(books) < num_books and page <= max_pages:
        url = f"{base_url}&page={page}"
        try:
            # Send a request to the URL
            response = requests.get(url, headers=headers, verify=False, timeout=30) # Added timeout
            print(f"Fetching: {url} [{response.status_code}]")
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            
            # Parse the content of the request with BeautifulSoup
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find book containers
            book_containers = soup.find_all("div", {"class": "s-result-item"})

            # If no books found on a page (after the first), it might be the end of results or a soft block
            if not book_containers and page > 1:
                print(f"No book containers found on page {page}. Assuming end of results or issue. Proceeding with fetched data.")
                break
            
            # Loop through the book containers and extract data
            for book_item in book_containers:
                title_element = book_item.find("h2", {"class": "a-size-base-plus a-spacing-none a-color-base a-text-normal"})
                author_element = book_item.find("span", {"class": "a-size-base"})
                price_element = book_item.find("span", {"class": "a-price-whole"})
                rating_element = book_item.find("span", {"class": "a-icon-alt"})
                
                if title_element and author_element and price_element and rating_element:
                    book_title = title_element.text.strip()
                    
                    if book_title not in seen_titles:
                        seen_titles.add(book_title)
                        books.append({
                            "Title": book_title,
                            "Author": author_element.text.strip(),
                            "Price": price_element.text.strip(),
                            "Rating": rating_element.text.strip(),
                        })
            
            if not book_containers and page == 1 and not books: # If first page has no books, something is wrong
                print(f"No book containers found on the first page ({url}). Check selectors or page structure.")
                break

            page += 1  # Increment page only on successful processing of a page
        
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred while fetching {url}: {e}. Proceeding with data fetched so far.")
            break
        except requests.exceptions.RequestException as e:
            print(f"Request exception (e.g., SSL, Timeout, Connection) occurred while fetching {url}: {e}. Proceeding with data fetched so far.")
            break
        except Exception as e:
            print(f"An unexpected error occurred during processing of page {url}: {e}. Proceeding with data fetched so far.")
            break

    # Limit to the requested number of books
    books = books[:num_books]
    
    if not books:
        print("No books were successfully fetched.")
        ti.xcom_push(key='book_data', value=[])
        return

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(books)
    
    # Remove duplicates based on 'Title' column
    if not df.empty:
        df.drop_duplicates(subset="Title", inplace=True)
    
    print(f"Successfully fetched {len(df) if not df.empty else 0} unique books.")
    if not df.empty:
        print("Sample of fetched data:")
        print(df.head())
    else:
        print("DataFrame is empty.")
        
    # Push the DataFrame to XCom
    ti.xcom_push(key='book_data', value=df.to_dict('records') if not df.empty else [])

def create_mysql_table_if_not_exists():
    mysql_hook = MySqlHook(mysql_conn_id='my_mysql')  # Use your MySQL connection ID in Airflow
    create_table_query = """
    CREATE TABLE IF NOT EXISTS books (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        authors VARCHAR(255),
        price VARCHAR(50),
        rating VARCHAR(50)
    );
    """
    mysql_hook.run(create_table_query)

#3) create and store data in table on mysql (load)
    
def insert_book_data_into_mysql(ti):
    book_data = ti.xcom_pull(key='book_data', task_ids='fetch_book_data')
    if not book_data:
        print("No book data found in XCom from fetch_book_data task. Skipping insertion.")
        return # Exit gracefully

    mysql_hook = MySqlHook(mysql_conn_id='my_mysql') # Ensure 'mysql_default' is your MySQL connection ID in Airflow
    insert_query = """
    INSERT INTO books (title, authors, price, rating)
    VALUES (%s, %s, %s, %s)
    """
    # MySqlHook's run method expects a list of tuples for parameters if executemany=False (which is the default)
    # or if you are inserting multiple rows in a single call with executemany=True.
    # For inserting one row at a time in a loop, parameters should be a tuple for each call.
    for book in book_data:
        mysql_hook.run(insert_query, parameters=(book['Title'], book['Author'], book['Price'], book['Rating']))

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fetech_amazon_data',
    default_args=default_args,
    description='A simple DAG to fetch data from Amazon',
    schedule_interval=timedelta(days=1),
)

# operators

fetch_book_data_task = PythonOperator(
    task_id='fetch_book_data',
    python_callable=get_amazon_data_books,
    op_kwargs={'num_books': 50},
    dag=dag,
)

create_table_task = PythonOperator(
    task_id='create_books_table',
    python_callable=create_mysql_table_if_not_exists,
    dag=dag,
)

insert_data_task = PythonOperator(
    task_id='insert_book_data',
    python_callable=insert_book_data_into_mysql,
    dag=dag,
)

# dependencies

fetch_book_data_task >> create_table_task >> insert_data_task
