# Rozproszony Generator Fraktali

## Opis Projektu
Projekt to zaawansowany system rozproszony do generowania zbioru Mandelbrota. Wykorzystuje architekturę **Master-Worker**, zaawansowaną komunikację sieciową oraz równoległość procesów.

## Kluczowe Funkcjonalności
1.  **Odporność na błędy (Fault Tolerance):**
    *   Serwer monitoruje czas pracy workerów.
    *   Jeśli worker nie zwróci wyniku w ciągu 30 sekund, jego zadanie jest automatycznie przywracane do kolejki i przydzielane innej maszynie.
2.  **Panel Monitoringu Webowego:**
    *   Wbudowany serwer **Flask** udostępnia interfejs pod adresem `http://localhost:5000`.
    *   Podgląd postępu w czasie rzeczywistym, statystyki zadań i lista aktywnych workerów wraz z ich statusem.
3.  **Dynamiczny Chunking:**
    *   Zadania są przydzielane w paczkach (chunkach), co optymalizuje narzut komunikacyjny.
4.  **Wieloprocesowość (Multiprocessing):**
    *   Worker automatycznie wykrywa liczbę rdzeni CPU i uruchamia odpowiednią liczbę procesów roboczych.
5.  **Kolorowanie i Estetyka:**
    *   Zmodyfikowane mapowanie kolorów dla bardziej atrakcyjnego wizualnie efektu końcowego.

## Obsługa Docker
Projekt został w pełni zdokeryzowany, co pozwala na uruchomienie całego klastra (Master + 3 Workery) jedną komendą.

### Wymagania
*   Docker
*   Docker Compose

### Uruchomienie klastra
```bash
docker-compose up --build
```
To polecenie zbuduje obrazy i uruchomi:
1.  **serwer-master** dostępny lokalnie pod portem `5001` (dashboard) i `65433` (socket).
2.  **3 instancje workerów**, które automatycznie połączą się z masterem.

### Skalowanie workerów w locie
Jeśli chcesz zwiększyć liczbę workerów do 5:
```bash
docker-compose up --scale worker=5
```

## Instrukcja Uruchomienia Lokalnego (bez Dockera)

### Wymagania
```bash
pip install Flask Pillow
```

### Krok po kroku
1.  **Uruchom Serwer:**
    ```bash
    python server.py
    ```
2.  **Otwórz Dashboard:**
    Przejdź w przeglądarce pod adres: `http://localhost:5001`
3.  **Uruchom Workerów:**
    ```bash
    python worker.py
    ```
4.  **Odbierz wynik:**
    Po zakończeniu pracy w katalogu głównym pojawi się plik `mandelbrot_advanced.png`.

## Architektura Techniczna
*   **Komunikacja:** Gniazda TCP, Serializacja Pickle.
*   **Synchronizacja:** Ryglowanie wątków (Threading Locks) na serwerze.
*   **Równoległość:** Pule procesów (Multiprocessing Queue) u workera.
