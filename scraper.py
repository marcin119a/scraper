import requests
import csv
from bs4 import BeautifulSoup
import time
import argparse
import os

BASE_URL = 'https://adresowo.pl'

CSV_HEADERS = [
    'locality',
    'street',
    'rooms',
    'area',
    'price_total_zl',
    'price_sqm_zl',
    'owner_type',
    'date_posted',
    'photo_count',
    'url',
    'image_url'
]

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def parse_listing(item):
    """
    Pobiera dane z pojedynczego elementu ogłoszenia (tagu <section>).
    Zwraca słownik lub None w przypadku błędu.
    """
    try:
        header = item.select_one('.result-info__header')
        location = header.strong.get_text(strip=True) if header and header.strong else ''
        address = header.select_one('.result-info__address').get_text(strip=True) if header and header.select_one('.result-info__address') else ''

        basics = item.select('.result-info__basic:not(.result-info__basic--owner)')
        rooms = basics[0].b.get_text(strip=True) if len(basics) > 0 and basics[0].b else ''
        area = basics[1].b.get_text(strip=True) if len(basics) > 1 and basics[1].b else ''

        price_total_tag = item.select_one('.result-info__price--total span')
        price_total = price_total_tag.get_text(strip=True).replace('\xa0', '') if price_total_tag else ''

        price_sqm_tag = item.select_one('.result-info__price--per-sqm span')
        price_sqm = price_sqm_tag.get_text(strip=True).replace('\xa0', '') if price_sqm_tag else ''

        owner_tag = item.select_one('.result-info__basic--owner')
        owner_type = owner_tag.get_text(strip=True) if owner_tag else 'Pośrednik'

        date_added_tag = item.select_one('.result-photo__date span')
        date_added = date_added_tag.get_text(strip=True) if date_added_tag else ''

        photo_count_tag = item.select_one('.result-photo__photos')
        photo_count = photo_count_tag.get_text(strip=True) if photo_count_tag else ''

        link_tag = item.select_one('a')
        link = BASE_URL + link_tag['href'] if link_tag and link_tag.has_attr('href') else ''

        image_tag = item.select_one('.result-photo__image')
        image_url = image_tag['src'] if image_tag and image_tag.has_attr('src') else ''

        return {
            'locality': location,
            'street': address,
            'rooms': rooms,
            'area': area,
            'price_total_zl': price_total,
            'price_sqm_zl': price_sqm,
            'owner_type': owner_type,
            'date_posted': date_added,
            'photo_count': photo_count,
            'url': link,
            'image_url': image_url,
        }

    except Exception as e:
        print(f"Błąd podczas parsowania ogłoszenia: {e}")
        return None


def scrape(city, pages, output_file):
    """
    Główna funkcja skryptu.

    Args:
        city (str): Nazwa miasta do scrapowania (np. 'lodz', 'warszawa', 'wroclaw')
        pages (int): Liczba stron do przetworzenia
        output_file (str): Ścieżka do pliku wyjściowego CSV
    """
    print(f"Rozpoczynam scraping {BASE_URL} dla miasta: {city}...")
    all_data = []

    with requests.Session() as session:
        session.headers.update(HTTP_HEADERS)

        for page_num in range(1, pages + 1):
            url = f'{BASE_URL}/mieszkania/{city}/_l{page_num}'
            print(f"Przetwarzanie strony {page_num}/{pages}: {url}")

            try:
                response = session.get(url, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')
                listings = soup.select('section.search-results__item')

                if not listings:
                    print(f"  -> Nie znaleziono ogłoszeń na stronie {page_num}. Prawdopodobnie strona nie istnieje.")
                    break

                print(f"  -> Znaleziono {len(listings)} ogłoszeń.")

                for item in listings:
                    row = parse_listing(item)
                    if row:
                        all_data.append(row)

                time.sleep(0.5)

            except requests.RequestException as e:
                print(f"Błąd podczas pobierania strony {url}: {e}")
                continue

    if all_data:
        print(f"\nZakończono scraping. Zapisywanie {len(all_data)} ogłoszeń do pliku {output_file}...")
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
                writer.writerows(all_data)
            print(f"Pomyślnie zapisano dane w pliku: {output_file}")
        except IOError as e:
            print(f"Błąd podczas zapisu do pliku {output_file}: {e}")
    else:
        print("\nNie zebrano żadnych danych.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scraper ogłoszeń nieruchomości z adresowo.pl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Przykłady użycia:
  python scraper.py
  python scraper.py --city warszawa --pages 5
  python scraper.py --city wroclaw --pages 10 --output data/ogloszenia_wroclaw.csv
        '''
    )

    parser.add_argument('--city', type=str, default='lodz',
                        help='Nazwa miasta do scrapowania (np. lodz, warszawa, wroclaw). Domyślnie: lodz')
    parser.add_argument('--pages', type=int, default=8,
                        help='Liczba stron do przetworzenia. Domyślnie: 8')
    parser.add_argument('--output', type=str, default=None,
                        help='Ścieżka do pliku wyjściowego CSV. Domyślnie: data/ogloszenia_{city}.csv')

    args = parser.parse_args()
    output_file = args.output or f'data/ogloszenia_{args.city}.csv'

    scrape(args.city, args.pages, output_file)
