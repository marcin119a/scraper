import re
import requests
import csv
from bs4 import BeautifulSoup
import time
import argparse
import os

BASE_URL = 'https://adresowo.pl'

CSV_HEADERS = [
    'ID',
    'Cena',
    'Metraż',
    'Pokoje',
    'Lokalizacja',
    'Ulica',
    'Typ',
    'Bez Pośredników',
    'Opis',
    'Link'
]

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def _clean(s):
    """Usuwa twarde spacje i normalizuje białe znaki."""
    if not s:
        return ''
    return s.replace('\xa0', ' ').strip()


def _parse_price(s):
    """Cena ze stringa (np. '635 000 zł') → int zł lub None."""
    if not s:
        return None
    digits = re.sub(r'[^\d]', '', s)
    if not digits:
        return None
    try:
        n = int(digits)
        return n if n > 0 else None
    except ValueError:
        return None


def _parse_area(s):
    """Metraż ze stringa (np. '50 m²', '50,25 m²') → float m² lub None."""
    if not s:
        return None
    s = s.replace(',', '.')
    m = re.search(r'[\d.]+', s)
    if not m:
        return None
    try:
        n = float(m.group(0))
        return n if n > 0 else None
    except ValueError:
        return None


def _parse_rooms(s):
    """Liczba pokoi ze stringa (np. '3', '3 pok.') → int lub None."""
    if not s:
        return None
    m = re.search(r'^\s*(\d+)\s*(?:pok\.?)?\s*$', s.strip(), re.IGNORECASE)
    if not m:
        m = re.search(r'(\d+)\s*pok', s, re.IGNORECASE)
    if not m:
        return None
    try:
        n = int(m.group(1))
        return n if n > 0 else None
    except (ValueError, IndexError):
        return None


def parse_listing(offer):
    """
    Pobiera dane z pojedynczego elementu ogłoszenia (div[data-offer-card]).
    Zwraca słownik lub None w przypadku błędu.
    """
    try:
        text = offer.get_text()
        text_lower = text.lower()

        offer_id = offer.get('data-id', '')

        stats = offer.select('p.flex-auto.text-base.text-neutral-800')
        price = ''
        area = ''
        rooms = ''
        if len(stats) > 0:
            bold = stats[0].find('span', class_='font-bold')
            price = _clean(bold.get_text()) if bold else ''
        if len(stats) > 1:
            bold = stats[1].find('span', class_='font-bold')
            area = _clean(bold.get_text()) if bold else ''
        if len(stats) > 2:
            bold = stats[2].find('span', class_='font-bold')
            rooms = _clean(bold.get_text()) if bold else ''

        link_tag = offer.find('a', href=True)
        link = ''
        if link_tag and link_tag.get('href'):
            href = link_tag['href']
            link = (BASE_URL + href) if not href.startswith('http') else href

        location_el = offer.select_one('span.line-clamp-1.font-bold')
        location = _clean(location_el.get_text()) if location_el else ''
        street_el = offer.select_one('span.line-clamp-1.text-neutral-900')
        street = _clean(street_el.get_text()) if street_el else ''

        is_private = 'Tak' if 'bez pośredników' in text_lower else 'Nie'

        desc_el = offer.select_one('p.line-clamp-4')
        description = _clean(desc_el.get_text()) if desc_el else ''

        return {
            'ID': offer_id,
            'Cena': _parse_price(price) if _parse_price(price) is not None else '',
            'Metraż': _parse_area(area) if _parse_area(area) is not None else '',
            'Pokoje': _parse_rooms(rooms) if _parse_rooms(rooms) is not None else '',
            'Lokalizacja': location,
            'Ulica': street,
            'Typ': 'Mieszkanie',
            'Bez Pośredników': is_private,
            'Opis': description,
            'Link': link,
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
                offers = soup.find_all('div', {'data-offer-card': True})

                if not offers:
                    print(f"  -> Nie znaleziono ogłoszeń na stronie {page_num}.")
                    break

                print(f"  -> Znaleziono {len(offers)} ogłoszeń.")

                for offer in offers:
                    row = parse_listing(offer)
                    if row:
                        all_data.append(row)

                time.sleep(1)

            except requests.RequestException as e:
                print(f"Błąd na stronie {page_num}: {e}")
                continue

    if all_data:
        print(f"\nZakończono! Zapisywanie {len(all_data)} ogłoszeń do {output_file}...")
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
                writer.writerows(all_data)
            print(f"Dane zapisano do: {output_file}")
        except IOError as e:
            print(f"Błąd zapisu do {output_file}: {e}")
    else:
        print("Nie zebrano żadnych danych.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scraper ogłoszeń nieruchomości z adresowo.pl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Przykłady:
  python scraper.py
  python scraper.py --city warszawa --pages 5
  python scraper.py --city wroclaw --pages 10 --output data/oferty_wroclaw.csv
'''
    )
    parser.add_argument('--city', type=str, default='lodz',
                        help='Miasto (np. lodz, warszawa, wroclaw). Domyślnie: lodz')
    parser.add_argument('--pages', type=int, default=8,
                        help='Liczba stron. Domyślnie: 8')
    parser.add_argument('--output', type=str, default=None,
                        help='Plik CSV. Domyślnie: data/ogloszenia_{city}.csv')

    args = parser.parse_args()
    output_file = args.output or f'data/ogloszenia_{args.city}.csv'
    scrape(args.city, args.pages, output_file)
