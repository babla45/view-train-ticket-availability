# Bangladesh Railway Ticket Explorer

A Python-based tool to search and analyze train ticket availability across Bangladesh's railway network. This project helps users find available train routes, seats, and fare information.


## 🚆 Features

- **Multi-route Search**: Search for tickets across multiple origin-destination combinations
- **Parallel Processing**: Efficiently handles multiple searches concurrently
- **Detailed Output**: Provides information on:
  - Train names and numbers
  - Departure and arrival times
  - Journey duration
  - Seat availability across different classes
  - Fare information
- **Station Schedule Analysis**: Extract complete station-by-station schedules including:
  - Arrival times
  - Departure times
  - Halt duration
  - Station-to-station travel times
- **Results Export**: Save search results for later analysis

## 📋 Prerequisites

- Python 3.8+
- [Playwright](https://playwright.dev/python/)


## 🛠️ Installation

1. Clone this repository:
```bash
git clone https://github.com/babla45/view-train-ticket-availability.git
cd view-train-ticket-availability
```

2. Install Playwright:
```bash
pip install playwright
```
3. Install Playwright browsers:
```bash
playwright install chromium
```

## 📊 Usage

### Ticket Availability Search

Run the main script to search for tickets:

```bash
python main.py
```

Follow the prompts to:
1. Select a search date
2. Choose station range to search
3. Set options for showing routes without available tickets





## 🔍 Sample Output In "output.txt" File

```
....................................................................................
........................|| _______ Md Babla Islam _______ ||........................
....................................................................................



Date: 27-Feb-2025

Summary: 
Total number of routes/combinations : 30
Total execution time                : 50.31 seconds (0.84 minutes)
Average execution time per route    : 1.68 seconds
Routes with seats                   : 15
Routes without seats                : 2
Routes with no train service        : 13




====================================================================================

From-To      : Khulna-Mubarakganj

(1) SAGARDARI EXPRESS (761) (04:00 PM-05:39 PM) [01h 39m]
   S_CHAIR   : 0    (৳105)

(2) SIMANTA EXPRESS (747) (09:15 PM-10:53 PM) [01h 38m]
   SNIGDHA   : 0    (৳196)
   S_CHAIR   : 0    (৳105)

(3) SUNDARBAN EXPRESS (725) (09:45 PM-11:23 PM) [01h 38m]
   S_CHAIR   : 8    (৳105)
   SNIGDHA   : 20   (৳196)

====================================================================================

From-To      : Khulna-Kotchandpur

(1) SAGARDARI EXPRESS (761) (04:00 PM-05:53 PM) [01h 53m]
   S_CHAIR   : 0    (৳120)

(2) SIMANTA EXPRESS (747) (09:15 PM-11:07 PM) [01h 52m]
   AC_B      : 0    (৳403)
   SNIGDHA   : 1    (৳225)
   S_CHAIR   : 0    (৳120)

(3) SUNDARBAN EXPRESS (725) (09:45 PM-11:37 PM) [01h 52m]
   S_CHAIR   : 6    (৳120)
   SNIGDHA   : 20   (৳225)

====================================================================================

From-To      : Khulna-Darshana_Halt

(1) SAGARDARI EXPRESS (761) (04:00 PM-06:23 PM) [02h 23m]
   S_CHAIR   : 26   (৳150)
   AC_S      : 0    (৳340)

(2) SIMANTA EXPRESS (747) (09:15 PM-11:34 PM) [02h 19m]
   AC_B      : 0    (৳506)
   SNIGDHA   : 4    (৳282)
   S_CHAIR   : 24   (৳150)

====================================================================================

From-To      : Khulna-Chuadanga

(1) SAGARDARI EXPRESS (761) (04:00 PM-06:45 PM) [02h 45m]
   S_CHAIR   : 0    (৳165)
   AC_S      : 0    (৳380)

(2) SIMANTA EXPRESS (747) (09:15 PM-11:56 PM) [02h 41m]
   AC_B      : 0    (৳564)
   SNIGDHA   : 0    (৳317)
   S_CHAIR   : 20   (৳165)
   F_BERTH   : 0    (৳380)

(3) SUNDARBAN EXPRESS (725) (09:45 PM-12:20 AM) [02h 35m]
   S_CHAIR   : 9    (৳165)
   AC_B      : 8    (৳564)
   SNIGDHA   : 34   (৳317)

====================================================================================

From-To      : Khulna-Alamdanga

(1) SAGARDARI EXPRESS (761) (04:00 PM-07:04 PM) [03h 04m]
   S_CHAIR   : 19   (৳185)

(2) SIMANTA EXPRESS (747) (09:15 PM-12:15 AM) [03h 00m]
   SNIGDHA   : 0    (৳351)
   S_CHAIR   : 17   (৳185)

(3) SUNDARBAN EXPRESS (725) (09:45 PM-12:39 AM) [02h 54m]
   S_CHAIR   : 18   (৳185)
   SNIGDHA   : 19   (৳351)

====================================================================================
No train found for route Daulatpur-Mubarakganj
====================================================================================
No train found for route Daulatpur-Kotchandpur
====================================================================================
No train found for route Daulatpur-Darshana_Halt
====================================================================================
No train found for route Daulatpur-Chuadanga
====================================================================================
No train found for route Daulatpur-Alamdanga
====================================================================================
No train found for route Noapara-Mubarakganj
====================================================================================
No train found for route Noapara-Kotchandpur
====================================================================================
No train found for route Noapara-Darshana_Halt
====================================================================================
Available 0 tickets for the route Noapara-Chuadanga
====================================================================================
No train found for route Noapara-Alamdanga
====================================================================================

From-To      : Jashore-Mubarakganj

(1) BENAPOLE EXPRESS (795) (02:15 PM-02:55 PM) [00h 40m]
   S_CHAIR   : 42   (৳50)
   SNIGDHA   : 5    (৳115)

(2) SUNDARBAN EXPRESS (725) (10:56 PM-11:23 PM) [00h 27m]
   S_CHAIR   : 12   (৳50)
   SNIGDHA   : 0    (৳115)

====================================================================================

From-To      : Jashore-Kotchandpur

(1) BENAPOLE EXPRESS (795) (02:15 PM-03:08 PM) [00h 53m]
   S_CHAIR   : 23   (৳50)
   SNIGDHA   : 0    (৳115)

(2) SUNDARBAN EXPRESS (725) (10:56 PM-11:37 PM) [00h 41m]
   S_CHAIR   : 40   (৳50)
   SNIGDHA   : 5    (৳115)

====================================================================================

From-To      : Jashore-Darshana_Halt

(1) BENAPOLE EXPRESS (795) (02:15 PM-03:34 PM) [01h 19m]
   S_CHAIR   : 9    (৳80)
   SNIGDHA   : 8    (৳156)

(2) SAGARDARI EXPRESS (761) (05:12 PM-06:23 PM) [01h 11m]
   S_CHAIR   : 0    (৳80)

====================================================================================

From-To      : Jashore-Chuadanga

(1) BENAPOLE EXPRESS (795) (02:15 PM-03:56 PM) [01h 41m]
   S_CHAIR   : 1    (৳100)
   SNIGDHA   : 8    (৳184)

(2) SAGARDARI EXPRESS (761) (05:12 PM-06:45 PM) [01h 33m]
   S_CHAIR   : 0    (৳100)

(3) SIMANTA EXPRESS (747) (10:26 PM-11:56 PM) [01h 30m]
   AC_B      : 0    (৳334)
   SNIGDHA   : 0    (৳184)
   S_CHAIR   : 0    (৳100)

(4) SUNDARBAN EXPRESS (725) (10:56 PM-12:20 AM) [01h 24m]
   S_CHAIR   : 50   (৳100)
   SNIGDHA   : 24   (৳184)

====================================================================================

From-To      : Jashore-Alamdanga

(1) SAGARDARI EXPRESS (761) (05:12 PM-07:04 PM) [01h 52m]
   S_CHAIR   : 0    (৳120)

(2) SUNDARBAN EXPRESS (725) (10:56 PM-12:39 AM) [01h 43m]
   S_CHAIR   : 13   (৳120)
   SNIGDHA   : 15   (৳225)

====================================================================================
No train found for route Mubarakganj-Kotchandpur
====================================================================================
Available 0 tickets for the route Mubarakganj-Darshana_Halt
====================================================================================

From-To      : Mubarakganj-Chuadanga

(1) BENAPOLE EXPRESS (795) (02:57 PM-03:56 PM) [00h 59m]
   S_CHAIR   : 8    (৳65)

(2) SAGARDARI EXPRESS (761) (05:41 PM-06:45 PM) [01h 04m]
   S_CHAIR   : 0    (৳65)

====================================================================================
No train found for route Mubarakganj-Alamdanga
====================================================================================

From-To      : Kotchandpur-Darshana_Halt

(1) CHITRA EXPRESS (763) (11:04 AM-11:28 AM) [00h 24m]
   SNIGDHA   : 0    (৳115)
   AC_S      : 0    (৳127)
   S_CHAIR   : 10   (৳50)

====================================================================================

From-To      : Kotchandpur-Chuadanga

(1) CHITRA EXPRESS (763) (11:04 AM-11:50 AM) [00h 46m]
   SNIGDHA   : 0    (৳115)
   AC_S      : 0    (৳127)
   S_CHAIR   : 3    (৳50)

(2) BENAPOLE EXPRESS (795) (03:10 PM-03:56 PM) [00h 46m]
   S_CHAIR   : 4    (৳50)

(3) SAGARDARI EXPRESS (761) (05:55 PM-06:45 PM) [00h 50m]
   S_CHAIR   : 0    (৳50)

(4) SUNDARBAN EXPRESS (725) (11:39 PM-12:20 AM) [00h 41m]
   S_CHAIR   : 10   (৳50)

====================================================================================
No train found for route Kotchandpur-Alamdanga
====================================================================================

From-To      : Darshana_Halt-Chuadanga

(1) CHITRA EXPRESS (763) (11:31 AM-11:50 AM) [00h 19m]
   SNIGDHA   : 0    (৳115)
   AC_S      : 0    (৳127)
   S_CHAIR   : 10   (৳50)

(2) SAGARDARI EXPRESS (761) (06:26 PM-06:45 PM) [00h 19m]
   S_CHAIR   : 0    (৳50)

====================================================================================
No train found for route Darshana_Halt-Alamdanga
====================================================================================

From-To      : Chuadanga-Alamdanga

(1) CHITRA EXPRESS (763) (11:53 AM-12:09 PM) [00h 16m]
   SNIGDHA   : 0    (৳115)
   AC_S      : 0    (৳127)
   S_CHAIR   : 10   (৳50)

(2) SAGARDARI EXPRESS (761) (06:48 PM-07:04 PM) [00h 16m]
   S_CHAIR   : 0    (৳50)



====================================================================================
|| ~~~~~~~~~~~~~~~~~~~~~~~~ ||   Finished Execution   || ~~~~~~~~~~~~~~~~~~~~~~~~ ||
====================================================================================

```


## Termanal Outputs:

```

....................................................................................................................
........................................|| _______  Find Tickets  _______ ||........................................
....................................................................................................................


Available stations:
-------------------

1: Khulna
2: Daulatpur       
3: Noapara
4: Jashore
5: Mubarakganj     
6: Kotchandpur     
7: Darshana_Halt   
8: Chuadanga       
9: Alamdanga       
10: Poradaha       
11: Bheramara      
12: Ishwardi       
13: Natore
14: Santahar       
15: Akkelpur       
16: Joypurhat      
17: Birampur       
18: Fulbari        
19: Parbatipur     
20: Saidpur        
21: Nilphamari     
22: Domar
23: Chilahati      

Use current date for search? (y/n): y
Enter starting station range: 19
Enter ending station range: 19
Include details for no trains/seats? (y/n): y

Processing routes...

 1. [✗] Completed ( Khulna to Parbatipur )            in 8.80s - remaining 17
 2. [✗] Completed ( Daulatpur to Parbatipur )         in 0.71s - remaining 16
 3. [✗] Completed ( Noapara to Parbatipur )           in 1.45s - remaining 15
 4. [✗] Completed ( Jashore to Parbatipur )           in 0.86s - remaining 14
 5. [✗] Completed ( Mubarakganj to Parbatipur )       in 0.82s - remaining 13
 6. [✗] Completed ( Kotchandpur to Parbatipur )       in 0.86s - remaining 12
 7. [✗] Completed ( Darshana_Halt to Parbatipur )     in 1.40s - remaining 11
 8. [✗] Completed ( Chuadanga to Parbatipur )         in 0.89s - remaining 10
 9. [✗] Completed ( Alamdanga to Parbatipur )         in 1.37s - remaining 9
10. [✗] Completed ( Poradaha to Parbatipur )          in 0.68s - remaining 8
11. [✗] Completed ( Bheramara to Parbatipur )         in 0.79s - remaining 7
12. [✗] Completed ( Ishwardi to Parbatipur )          in 1.13s - remaining 6
13. [✓] Completed ( Natore to Parbatipur )            in 1.60s - remaining 5
14. [✓] Completed ( Santahar to Parbatipur )          in 1.95s - remaining 4
15. [✓] Completed ( Akkelpur to Parbatipur )          in 1.51s - remaining 3
16. [✓] Completed ( Joypurhat to Parbatipur )         in 2.04s - remaining 2
17. [✓] Completed ( Birampur to Parbatipur )          in 1.51s - remaining 1
18. [✓] Completed ( Fulbari to Parbatipur )           in 1.09s - remaining 0



------------------------------  Summary  ----------------------------------

Routes with available seats: 6/18 (33.3%)
Routes without available seats: 6/18 (33.3%)
Routes with no train service: 6/18 (33.3%)

Total execution time: 42.95 seconds (0.72 minutes) for 18 routes
Average execution time per route: 2.39s

------------------------  Execution completed  ----------------------------


Results are saven in output.txt file.

```

## 📝 Notes

- This project uses the official Bangladesh Railway e-ticket portal for data
- Search results depend on the availability of seats at the time of search
- Some routes may not have direct train services

## 🛡️ Legal and Ethical Considerations

This tool is designed for personal use and research purposes only. It respects the following principles:

- Does not bypass any security measures
- Uses reasonable request rates to avoid server load
- Does not store personal information
- Is not intended for ticket scalping or any other activity that violates Bangladesh Railway's terms of service


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
