import requests
import csv
from bs4 import BeautifulSoup
import time
import argparse

# Stałe
BASE_URL = 'https://adresowo.pl'

# Nagłówki CSV (wszystkie dane jako stringi)
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

# Nagłówki HTTP, aby udawać przeglądarkę
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def parse_listing(item):
    """
    Pobiera dane z pojedynczego elementu ogłoszenia (tagu <section>).
    Zwraca listę stringów lub None w przypadku błędu.
    """
    try:
        # --- Lokalizacja i Ulica ---
        header = item.select_one('.result-info__header')
        location = header.strong.get_text(strip=True) if header and header.strong else ''
        address = header.select_one('.result-info__address').get_text(strip=True) if header and header.select_one('.result-info__address') else ''

        # --- Pokoje i Metraż ---
        basics = item.select('.result-info__basic:not(.result-info__basic--owner)')
        rooms = basics[0].b.get_text(strip=True) if len(basics) > 0 and basics[0].b else ''
        area = basics[1].b.get_text(strip=True) if len(basics) > 1 and basics[1].b else ''

        # --- Ceny ---
        # Używamy .replace('\xa0', '') do usunięcia twardych spacji (nbsp)
        price_total_tag = item.select_one('.result-info__price--total span')
        price_total = price_total_tag.get_text(strip=True).replace('\xa0', '') if price_total_tag else ''

        price_sqm_tag = item.select_one('.result-info__price--per-sqm span')
        price_sqm = price_sqm_tag.get_text(strip=True).replace('\xa0', '') if price_sqm_tag else ''

        # --- Typ Oferty (Bezpośrednio lub Pośrednik) ---
        owner_tag = item.select_one('.result-info__basic--owner')
        # Zakładamy, że jeśli nie ma tagu "Bez pośredników", to jest to oferta od pośrednika
        owner_type = owner_tag.get_text(strip=True) if owner_tag else 'Pośrednik'

        # --- Dane z sekcji zdjęcia ---
        date_added_tag = item.select_one('.result-photo__date span')
        date_added = date_added_tag.get_text(strip=True) if date_added_tag else ''

        photo_count_tag = item.select_one('.result-photo__photos')
        # .get_text(strip=True) inteligentnie pominie ikonę SVG i weźmie samą liczbę
        photo_count = photo_count_tag.get_text(strip=True) if photo_count_tag else ''

        # --- Linki ---
        link_tag = item.select_one('a')
        link = BASE_URL + link_tag['href'] if link_tag and link_tag.has_attr('href') else ''

        image_tag = item.select_one('.result-photo__image')
        image_url = image_tag['src'] if image_tag and image_tag.has_attr('src') else ''

        # Zwracamy listę stringów zgodną z nagłówkami CSV
        return [
            location,
            address,
            rooms,
            area,
            price_total,
            price_sqm,
            owner_type,
            date_added,
            photo_count,
            link,
            image_url
        ]

    except Exception as e:
        print(f"Błąd podczas parsowania ogłoszenia: {e}")
        return None

def main(city, pages, output_file):
    """
    Główna funkcja skryptu.
    
    Args:
        city (str): Nazwa miasta do scrapowania (np. 'lodz', 'warszawa', 'wroclaw')
        pages (int): Liczba stron do przetworzenia
        output_file (str): Ścieżka do pliku wyjściowego CSV
    """
    print(f"Rozpoczynam scraping {BASE_URL} dla miasta: {city}...")
    all_data = []

    # Używamy sesji, aby utrzymać połączenie i nagłówki
    with requests.Session() as session:
        session.headers.update(HTTP_HEADERS)

        # Pętla przez określoną liczbę stron
        for page_num in range(1, pages + 1):
            url = f'https://adresowo.pl/mieszkania/{city}/_l{page_num}'
            print(f"Przetwarzanie strony {page_num}/{pages}: {url}")

            try:
                response = session.get(url, timeout=10)
                # Sprawdzamy, czy żądanie się powiodło (kod 2xx)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Znajdujemy wszystkie kontenery ogłoszeń na stronie
                listings = soup.select('section.search-results__item')

                if not listings:
                    print(f"  -> Nie znaleziono ogłoszeń na stronie {page_num}. Prawdopodobnie strona nie istnieje.")
                    break # Przerywamy pętlę, jeśli nie ma więcej ogłoszeń

                print(f"  -> Znaleziono {len(listings)} ogłoszeń.")

                # Przechodzimy przez każde ogłoszenie
                for item in listings:
                    data_row = parse_listing(item)
                    if data_row:
                        all_data.append(data_row)

                # Mała przerwa, aby nie obciążać serwera
                time.sleep(0.5)

            except requests.RequestException as e:
                print(f"Błąd podczas pobierania strony {url}: {e}")
                continue # Przechodzimy do następnej strony

    # --- Zapis do pliku CSV ---
    if all_data:
        print(f"\nZakończono scraping. Zapisywanie {len(all_data)} ogłoszeń do pliku {output_file}...")
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)  # Zapis nagłówka
                writer.writerows(all_data)    # Zapis wszystkich danych
            print(f"Pomyślnie zapisano dane w pliku: {output_file}")
        except IOError as e:
            print(f"Błąd podczas zapisu do pliku {output_file}: {e}")
    else:
        print("\nNie zebrano żadnych danych.")

# Uruchomienie głównej funkcji
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scraper ogłoszeń nieruchomości z adresowo.pl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Przykłady użycia:
  # Scrapuj 8 stron dla Łodzi (domyślne, zapisuje do scraper/data/)
  python scrape.py
  
  # Scrapuj 5 stron dla Warszawy
  python scrape.py --city warszawa --pages 5
  
  # Scrapuj 10 stron dla Wrocławia z własną nazwą pliku
  python scrape.py --city wroclaw --pages 10 --output scraper/data/ogloszenia_wroclaw.csv
        '''
    )
    
    parser.add_argument(
        '--city',
        type=str,
        default='lodz',
        help='Nazwa miasta do scrapowania (np. lodz, warszawa, wroclaw). Domyślnie: lodz'
    )
    
    parser.add_argument(
        '--pages',
        type=int,
        default=8,
        help='Liczba stron do przetworzenia. Domyślnie: 8'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Ścieżka do pliku wyjściowego CSV. Domyślnie: scraper/data/ogloszenia_{city}.csv'
    )
    
    args = parser.parse_args()
    
    # Jeśli nie podano nazwy pliku, generujemy ją na podstawie miasta i zapisujemy w data/
    if args.output:
        output_file = args.output
    else:
        import os
        os.makedirs('scraper/data', exist_ok=True)
        output_file = f'scraper/data/ogloszenia_{args.city}.csv'
    
    main(args.city, args.pages, output_file)