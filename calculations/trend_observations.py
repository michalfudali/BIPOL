"""User-sourced catalogue supplements; never modify the shared reference data."""
import csv
import io
import math

FIELDS = {'climb_rate_ms': (0, 150), 'takeoff_distance_m': (1, 20000),
          'landing_distance_m': (1, 20000), 'year': (1900, 2100)}


def validate_observations(rows):
    from calculations.trends import load_aircraft
    known = {r['id'] for r in load_aircraft()}
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError('Uzupełnienia próby: wymagana lista do 1000 obserwacji.')
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] not in known:
            raise ValueError('Uzupełnienie musi wskazywać identyfikator konstrukcji z bazy.')
        if row['id'] in seen:
            raise ValueError('Powtórzony identyfikator konstrukcji w uzupełnieniach.')
        seen.add(row['id'])
        clean = {'id': row['id']}
        for key, (low, high) in FIELDS.items():
            value = row.get(key)
            if value in ('', None):
                continue
            try:
                number = float(str(value).replace(',', '.'))
            except (ValueError, TypeError):
                raise ValueError(f'Uzupełnienie {key}: podaj liczbę.') from None
            if isinstance(value, bool) or not math.isfinite(number) or not low <= number <= high:
                raise ValueError(f'Uzupełnienie {key}: wymagany zakres {low}–{high}.')
            if key == 'year' and not number.is_integer():
                raise ValueError('Rok certyfikacji musi być liczbą całkowitą.')
            clean[key] = number
        if len(clean) == 1:
            continue
        source = row.get('source', '')
        if not isinstance(source, str) or not 5 <= len(source.strip()) <= 2000:
            raise ValueError('Każdy uzupełniony wiersz wymaga źródła: dokument, strona/URL i warunki pomiaru.')
        clean['source'] = source.strip()
        result.append(clean)
    return result


def import_observations(text):
    if len(text) > 1_000_000:
        raise ValueError('Plik uzupełnień może mieć maksymalnie 1 MB.')
    text = text.lstrip('\ufeff')
    if not text.strip():
        raise ValueError('Plik CSV jest pusty.')
    delimiter = ';' if ';' in text.splitlines()[0] else ','
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames or not {'id', 'source'} <= set(reader.fieldnames):
        raise ValueError('CSV wymaga nagłówków id i source oraz kolumn parametrów z szablonu.')
    return validate_observations(list(reader))
