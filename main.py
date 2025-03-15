from playwright.sync_api import sync_playwright
# import re
import concurrent.futures
from datetime import datetime, timedelta
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
import time
# import os
import io
from multiprocessing import Value

# Constants for performance tuning
MAX_WORKERS = 6  # Increased parallel browser instances
BATCH_SIZE = 40  # Larger batches reduce browser launch overhead
NAVIGATION_TIMEOUT = 15000  # 15 seconds
SELECTOR_TIMEOUT = 10000   # 10 seconds
# Add counters for routes with and without seats
ROUTES_WITH_SEATS = Value('i', 0)
ROUTES_WITHOUT_SEATS = Value('i', 0)

def doubleEqualLine(file):
    file.write('='*84 + '\n')

def endExecution(file):
    file.write("\n\n")
    file.write('='*84 + '\n')
    file.write('|| ' + '~'*24 + ' ||   Finished Execution   || ' + '~'*24 + ' ||\n')
    file.write('='*84 + '\n')

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
        # Removed redundant navigation reset
        # page.goto('about:blank', wait_until='commit', timeout=NAVIGATION_TIMEOUT)
        page.goto(url, wait_until='domcontentloaded', timeout=NAVIGATION_TIMEOUT)
        
        # Wait for critical elements with optimized timeout
        page.wait_for_selector('span.all-seats.text-left, span.no-ticket-found-first-msg', timeout=SELECTOR_TIMEOUT)

        # Check if no trains are found
        no_trains_el = page.query_selector('span.no-ticket-found-first-msg')
        if no_trains_el:
            if show_no_train_details:
                output_buffer.write(f"\nDate          : {formatted_date}\nFrom-To       : {from_station}-{to_station}\n✗ No train found for selected dates or cities. Please try different dates or cities.\n\n")
            else:
                output_buffer.write(f"Date: {formatted_date} - No train found for route {from_station}-{to_station}\n")
            return output_buffer.getvalue(), False
        
        # Quick check for any available seats using optimized selector
        available_seat = page.query_selector('.all-seats.text-left:not(:text-is("0"))')
        has_available_seats = available_seat is not None

        # Update the seat availability counters
        if has_available_seats:
            with ROUTES_WITH_SEATS.get_lock():
                ROUTES_WITH_SEATS.value += 1
        else:
            with ROUTES_WITHOUT_SEATS.get_lock():
                ROUTES_WITHOUT_SEATS.value += 1

        if not has_available_seats and not show_no_train_details:
            output_buffer.write(f"Date: {formatted_date} - Available 0 tickets for the route {from_station}-{to_station}\n")
            return output_buffer.getvalue(), False

        # Only process full details when necessary
        output_buffer.write(f"\n    Date      : {formatted_date}\n    From-To   : {from_station}-{to_station}")
        output_buffer.write(f"\n    URL       : {url}\n\n")
        
        train_elements = page.query_selector_all('app-single-trip')
        for index, train_el in enumerate(train_elements, 1):
            train_name = train_el.query_selector('h2[style="text-transform: uppercase;"]')
            journey_duration = train_el.query_selector('.journey-duration').inner_text()
            if not train_name:
                continue

            # Efficient time extraction
            times = train_el.evaluate('''el => {
                const start = el.querySelector('.journey-start .journey-date')?.innerText.split(', ')[1] || 'N/A';
                const end = el.querySelector('.journey-end .journey-date')?.innerText.split(', ')[1] || 'N/A';
                return {start, end};
            }''')
            
            output_buffer.write(f"({index}) {train_name.inner_text()} ({times['start']}-{times['end']}) [{journey_duration}]\n")
            
            # Consolidated seat data extraction
            seats_data = train_el.evaluate('''el => {
                return [...el.querySelectorAll('.single-seat-class')].map(seat => ({
                    class_name: seat.querySelector('.seat-class-name')?.innerText || '',
                    fare: seat.querySelector('.seat-class-fare')?.innerText || '',
                    count: seat.querySelector('.all-seats.text-left')?.innerText || '0'
                }));
            }''')
            
            for seat in seats_data:
                output_buffer.write(f"    {seat['class_name']:<10}: {seat['count']:<4} ({seat['fare']})\n")
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
                error_output = f"\nJourney Date: {formatted_date}\n\nFrom Station : {from_station}\nTo Station   : {to_station}\n\nError: {str(e)}\n\n"
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
            return [datetime.now().strftime("%d-%m-%Y")]
        elif use_current == 'n':
            # Display next 11 days (including today) as a list
            today = datetime.now()
            dates = [(today + timedelta(days=i)) for i in range(11)]
            
            print("\nAvailable dates for search:")
            for idx, date in enumerate(dates, 1):
                date_str = date.strftime("%d-%m-%Y")
                print(f"{idx}: {date_str} ({date.strftime('%A')})")
            
            print("\nYou can enter:")
            print("- A specific date number (e.g., '3')")
            print("- A range of dates (e.g., '1-5')")
            print("- Multiple dates separated by commas (e.g., '1,3,5')")
            
            while True:
                date_input = input("\nEnter your date selection: ")
                selected_dates = []
                
                # Check if input is a range (e.g., "1-5")
                if '-' in date_input and ',' not in date_input:
                    try:
                        start, end = map(int, date_input.split('-'))
                        if 1 <= start <= end <= 11:
                            selected_dates = [dates[i-1].strftime("%d-%m-%Y") for i in range(start, end+1)]
                        else:
                            print("Invalid range. Please use numbers between 1 and 11.")
                            continue
                    except ValueError:
                        print("Invalid range format. Use format like '1-5'.")
                        continue
                # Check if input is a comma-separated list
                elif ',' in date_input:
                    try:
                        indices = [int(idx.strip()) for idx in date_input.split(',')]
                        if all(1 <= idx <= 11 for idx in indices):
                            selected_dates = [dates[idx-1].strftime("%d-%m-%Y") for idx in indices]
                        else:
                            print("Invalid selection. Please use numbers between 1 and 11.")
                            continue
                    except ValueError:
                        print("Invalid format. Use comma-separated numbers like '1,3,5'.")
                        continue
                # Check if input is a single number
                else:
                    try:
                        idx = int(date_input)
                        if 1 <= idx <= 11:
                            selected_dates = [dates[idx-1].strftime("%d-%m-%Y")]
                        else:
                            print("Invalid selection. Please use a number between 1 and 11.")
                            continue
                    except ValueError:
                        print("Invalid input. Please enter a number, range, or comma-separated list.")
                        continue
                
                # Confirm dates are in valid format
                if all(validate_date(date) for date in selected_dates):
                    return selected_dates
                
                print("Invalid date selection. Please try again.")
        
        print("Please enter 'y' or 'n'")

if __name__ == "__main__":
    overall_start = time.time()
    
    with open('stations.txt', 'r') as file:
        stations = [line.strip() for line in file.readlines()]
    
    print(f"\n{'.' * 116}\n{'.' * 40}|| _______  Find Tickets  _______ ||{'.' * 40}\n{'.' * 116}\n")
    print("\nAvailable stations:\n-------------------\n")
    for idx, station in enumerate(stations, 1):
        print(f"{idx}: {station}")
    print("")

    date_list = get_search_date()
    
    start_index = int(input("Enter starting station range: ")) - 1
    end_index = int(input("Enter ending station range: ")) - 1
    show_no_train_details = input("Include details for no trains/seats? (y/n): ").lower() == 'y'
    print("\nProcessing routes...\n")

    station_combinations = []
    route_index = 0
    for i in range(len(stations)):
        for j in range(max(i+1, start_index), min(end_index+1, len(stations))):
            from_station = stations[i]
            to_station = stations[j]
            station_combinations.append((from_station, to_station, route_index))
            route_index += 1

    total_combinations = len(station_combinations) * len(date_list)
    
    # Dictionary to store results for all dates
    all_results_by_date = {}
    
    for date_str in date_list:
        # Reset counters for each date
        ROUTES_WITH_SEATS.value = 0
        ROUTES_WITHOUT_SEATS.value = 0
        
        formatted_date = convert_date_format(date_str)
        print(f"\nProcessing for date: {formatted_date}\n")
        
        batches = [station_combinations[i:i+BATCH_SIZE] for i in range(0, len(station_combinations), BATCH_SIZE)]
        completed_routes_counter = Value('i', 0)
        date_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_batch, batch, formatted_date, completed_routes_counter, len(station_combinations), show_no_train_details) for batch in batches]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_results = future.result()
                    date_results.extend(batch_results)
                except Exception as e:
                    print(f"Batch generated exception: {e}")

        date_results.sort(key=lambda x: x[2])
        all_results_by_date[date_str] = {
            'results': date_results,
            'with_seats': ROUTES_WITH_SEATS.value,
            'without_seats': ROUTES_WITHOUT_SEATS.value
        }
    
    # Calculate overall statistics
    total_routes_with_seats = sum(data['with_seats'] for data in all_results_by_date.values())
    total_routes_without_seats = sum(data['without_seats'] for data in all_results_by_date.values())
    total_no_train_routes = total_combinations - (total_routes_with_seats + total_routes_without_seats)
    total_time = time.time() - overall_start
    minutes = total_time / 60
    
    # Print summary once at the end
    print("\n\n\n------------------------------  Summary  ----------------------------------\n")
    print(f"Total routes processed: {total_combinations} (across {len(date_list)} date(s))")
    print(f"Routes with available seats: {total_routes_with_seats}/{total_combinations} ({total_routes_with_seats/total_combinations*100:.1f}%)")
    print(f"Routes without available seats: {total_routes_without_seats}/{total_combinations} ({total_routes_without_seats/total_combinations*100:.1f}%)")
    print(f"Routes with no train service: {total_no_train_routes}/{total_combinations} ({total_no_train_routes/total_combinations*100:.1f}%)")
    
    # Write to file
    with open('output.txt', 'w', encoding='utf-8') as output_file:
        output_file.write(f"\n{'.' * 84}\n{'.' * 24}|| _______ Md Babla Islam _______ ||{'.' * 24}\n{'.' * 84}\n\n\n\n")
        output_file.write(f"Summary: \n\n")
        output_file.write("Execution date and time             : " + datetime.now().strftime("%Y-%m-%d %I:%M:%S %p") + '\n')
        output_file.write(f"Journey Dates                       : {', '.join(convert_date_format(d) for d in date_list)}\n")
        output_file.write(f"Total number of routes/combinations : {total_combinations}\n")
        output_file.write(f"Total execution time                : {total_time:.2f} seconds ({minutes:.2f} minutes)\n")
        output_file.write(f"Average execution time per route    : {total_time/total_combinations:.2f} seconds\n")
        output_file.write(f"Routes with seats                   : {total_routes_with_seats}\nRoutes without seats                : {total_routes_without_seats}\nRoutes with no train service        : {total_no_train_routes}\n\n\n\n\n")
        
        # Write results for all dates
        for date_str in date_list:
            formatted_date = convert_date_format(date_str)
            output_file.write(f"{'=' * 84}\n")
            output_file.write(f"RESULTS FOR DATE: {formatted_date}\n")
            output_file.write(f"{'=' * 84}\n\n")
            
            for result in all_results_by_date[date_str]['results']:
                doubleEqualLine(output_file)
                output_file.write(result[3])
                
        endExecution(output_file)

    print(f"\nTotal execution time: {total_time:.2f} seconds ({minutes:.2f} minutes) for {total_combinations} routes")
    print(f"Average execution time per route: {total_time/total_combinations:.2f}s")
    print("\n------------------------  Execution completed  ----------------------------\n")
    print("\nResults are saved in output.txt file.\n\n")
