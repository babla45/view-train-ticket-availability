from playwright.sync_api import sync_playwright
import re
import concurrent.futures
from datetime import datetime
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
import time
import os
import io
from multiprocessing import Value

# Constants for performance tuning
MAX_WORKERS = 6  # Increased parallel browser instances
BATCH_SIZE = 24  # Larger batches reduce browser launch overhead
NAVIGATION_TIMEOUT = 15000  # 15 seconds
SELECTOR_TIMEOUT = 10000   # 10 seconds

def doubleEqualLine(file):
    file.write('='*117 + '\n')

def endExecution(file):
    file.write("\n\n")
    file.write('='*117 + '\n')
    file.write('||' + '~'*43 + '||   Finished Execution    ||' + '~'*41 + '||\n')
    file.write('='*117 + '\n')

def validate_date(date_str):
    try:
        return bool(datetime.strptime(date_str, "%d-%m-%Y"))
    except ValueError:
        return False

def convert_date_format(date_str):
    date_obj = datetime.strptime(date_str, "%d-%m-%Y")
    return date_obj.strftime("%d-%b-%Y")

def process_route(page, from_station, to_station, formatted_date, show_no_train_details):
    """Process a single route using a shared page"""
    url = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={from_station}&tocity={to_station}&doj={formatted_date}&class=S_CHAIR"
    output_buffer = io.StringIO()
    has_available_seats = False

    try:
        # Reset page state before navigation
        page.goto('about:blank', wait_until='commit', timeout=NAVIGATION_TIMEOUT)
        
        # Faster navigation with reduced wait requirements
        page.goto(url, wait_until='domcontentloaded', timeout=NAVIGATION_TIMEOUT)
        
        # Wait for critical elements with optimized timeout
        page.wait_for_selector('span.all-seats.text-left, span.no-ticket-found-first-msg', timeout=SELECTOR_TIMEOUT)

        # Check if no trains are found
        no_trains_el = page.query_selector('span.no-ticket-found-first-msg')
        if no_trains_el:
            if show_no_train_details:
                output_buffer.write(f"\nDate         : {formatted_date}\nFrom-To      : {from_station}-{to_station}\n\nNo train found for selected dates or cities.\nPlease try different dates or cities.\n\n")
            else:
                output_buffer.write(f"No train found for route {from_station}-{to_station}\n")
            return output_buffer.getvalue(), False
        
        # Quick check for any available seats using optimized selector
        available_seat = page.query_selector('.all-seats.text-left:not(:text-is("0"))')
        has_available_seats = available_seat is not None

        if not has_available_seats and not show_no_train_details:
            output_buffer.write(f"Available 0 tickets for the route {from_station}-{to_station}\n")
            return output_buffer.getvalue(), False

        # Only process full details when necessary
        output_buffer.write(f"\nDate         : {formatted_date}\nFrom-To      : {from_station}-{to_station}\n\n")
        
        train_elements = page.query_selector_all('app-single-trip')
        for index, train_el in enumerate(train_elements, 1):
            train_name = train_el.query_selector('h2[style="text-transform: uppercase;"]')
            if not train_name:
                continue

            # Efficient time extraction
            times = train_el.evaluate('''el => {
                const start = el.querySelector('.journey-start .journey-date')?.innerText.split(', ')[1] || 'N/A';
                const end = el.querySelector('.journey-end .journey-date')?.innerText.split(', ')[1] || 'N/A';
                return {start, end};
            }''')
            
            output_buffer.write(f"({index}) {train_name.inner_text()} ({times['start']}-{times['end']})\n")
            
            # Bulk seat information extraction
            seats_data = train_el.evaluate('''el => {
                return Array.from(el.querySelectorAll('.single-seat-class')).map(seat => {
                    const class_name = seat.querySelector('.seat-class-name')?.innerText || '';
                    const fare = seat.querySelector('.seat-class-fare')?.innerText || '';
                    const count = seat.querySelector('.all-seats.text-left')?.innerText || '0';
                    return {class_name, fare, count};
                });
            }''')
            
            for seat in seats_data:
                output_buffer.write(f"   {seat['class_name']:<10}: {seat['count']:<4} ({seat['fare']})\n")
            output_buffer.write("\n")

    except PlaywrightTimeoutError:
        output_buffer.write(f"Timeout error accessing {from_station} to {to_station}\n\n")
    except Exception as e:
        output_buffer.write(f"Error processing {from_station} to {to_station}: {str(e)}\n\n")
    
    return output_buffer.getvalue(), has_available_seats

def process_batch(route_batch, formatted_date, completed_routes_counter, total_combinations, show_no_train_details):
    """Process a batch of routes using a single browser and page"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        results = []
        for from_station, to_station, route_index in route_batch:
            start_time = time.time()
            try:
                output_text, has_seats = process_route(page, from_station, to_station, formatted_date, show_no_train_details)
                elapsed_time = time.time() - start_time
                results.append((from_station, to_station, route_index, output_text, has_seats))

                with completed_routes_counter.get_lock():
                    completed_routes_counter.value += 1
                    completed = completed_routes_counter.value
                    remaining = total_combinations - completed

                route_text = f"( {from_station} to {to_station} )"
                count_width = len(str(total_combinations))
                status = "✓" if has_seats else "✗"
                print(f"{completed:>{count_width}}. [{status}] Completed {route_text:<35} in {elapsed_time:.2f}s - remaining {remaining}")

            except Exception as e:
                error_output = f"\nDate: {formatted_date}\n\nFrom Station : {from_station}\nTo Station   : {to_station}\n\nError: {str(e)}\n\n"
                results.append((from_station, to_station, route_index, error_output, False))
                with completed_routes_counter.get_lock():
                    completed_routes_counter.value += 1
                print(f"Error processing {from_station} to {to_station}: {str(e)}")

        page.close()
        context.close()
        browser.close()
        return results

def get_search_date():
    while True:
        use_current = input("Use current date for search? (y/n): ").lower()
        if use_current == 'y':
            return datetime.now().strftime("%d-%m-%Y")
        elif use_current == 'n':
            while True:
                date_str = input("Enter date (dd-mm-yyyy): ")
                if validate_date(date_str):
                    return date_str
                print("Invalid date format. Please use dd-mm-yyyy format.")
        print("Please enter 'y' or 'n'")

if __name__ == "__main__":
    overall_start = time.time()
    
    with open('stations.txt', 'r') as file:
        stations = [line.strip() for line in file.readlines()]

    print("\nAvailable stations:\n------------------")
    for idx, station in enumerate(stations, 1):
        print(f"{idx}: {station}")

    date_str = get_search_date()
    formatted_date = convert_date_format(date_str)

    start_index = int(input("Enter starting station range: ")) - 1
    end_index = int(input("Enter ending station range: ")) - 1
    show_no_train_details = input("Include details for no trains/seats? (y/n): ").lower() == 'y'

    station_combinations = []
    route_index = 0
    for i in range(len(stations)):
        for j in range(max(i+1, start_index), min(end_index+1, len(stations))):
            from_station = stations[i]
            to_station = stations[j]
            station_combinations.append((from_station, to_station, route_index))
            route_index += 1

    total_combinations = len(station_combinations)
    batches = [station_combinations[i:i+BATCH_SIZE] for i in range(0, len(station_combinations), BATCH_SIZE)]

    completed_routes_counter = Value('i', 0)
    all_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_batch, batch, formatted_date, completed_routes_counter, total_combinations, show_no_train_details) for batch in batches]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
            except Exception as e:
                print(f"Batch generated exception: {e}")

    all_results.sort(key=lambda x: x[2])
    
    with open('output.txt', 'w', encoding='utf-8') as output_file:
        for result in all_results:
            doubleEqualLine(output_file)
            output_file.write(result[3])
        endExecution(output_file)

    total_time = time.time() - overall_start
    print(f"\nTotal execution time: {total_time:.2f}s for {total_combinations} routes")
    print(f"Average time per route: {total_time/total_combinations:.2f}s")
    print("-----------------Execution completed--------------------")