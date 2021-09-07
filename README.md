Project: STONKS

A web app to quote stock prices in real time via IEX API and dummy buy/ sell with transaction history.

Open photos folder to view page samples.

Backend Language: Python (Flask)
Structure/ Style Tools: HTML5, CSS3
Frontend Language: JavaScript, Jinja Template language
API: IEX Cloud stock quote

Features:

1. Register and Login user with hashed passwords.(Passwords are saved and matched using hash functions from the werkzeug.security module.)

2. Allow user to quote stock prices by typing in the stock symbol.

3. Allow user to add cash into the account.

4. Allow user to dummy buy stocks and store that info in transactions history record with date & time, company, symbol and number of stocks bought with total cash in hand.

5. Allow user to sell owned stocks by selecting stock symbol from dropdown and store transaction history with a '-' sign.
