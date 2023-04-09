# BlutspenderBot
Telegram Bot for checking blood donation appointements nearby
you have to change "betelgeitze" to smth else like your docker login name

## Encouragment
This is a non-commercial project.
Currently this bot is working for Germany. You can find it under: https://t.me/BlutspenderBot  
I encourage you to build such a bot for your country of living (if it is not Germany). You can use this project as the basis.  
To do so, you need to:
1. Rewrite parser.py to parse blood donation appointments from your country
2. Change county_code in config.json to your country code.
3. Deploy the bot

If you need help or want to exchange ideas, write me a message.

## Installation

1. Register a bot in Telegram using BotFather.
  1. Get your Bot API Token
2. Clone this repository to your local machine
3. Create .env file
  1. Create the following variables inside:
    BOT_API_KEY=<paste api key from step 1.1>  
    POSTGRES_DB=<think of a name>  
    HOSTNAME=<think of a name>  
    PORT_ID=5432  
    POSTGRES_PASSWORD=<think of a pass>  
    POSTGRES_USER=<think of a name>  
   2. Save the file on the same level with config.json
 4. Open config.json
   1. Explanation of variables:
    delta - parses the appointments for the next 8 days  
    offset - from what day the parsing should start.   
    country_code - the country where you want to run blood donation appointments  
    inform_days - how many days before your users should be reminded  
    max_distance - max distance between a postcode that user inserted to a postcode with available blood donation appointment  
    approximate_max_distance - used for improving performance of your database. Should be 5km bigger than max_distance, but you can play with the number if you want  
    add_timeout - timeout for users to add a postcode  
    feedback_timeout - timeout for users to add feedback  
  2.Change country_code to your country code
  3.Change offset to 0 (after you successfully run parser for the first time, you should change it to 8, so it is the same value as delta. If you plan to run parser every day, the delta should equal to offset after the first run)
 5. 
    

## Deployment


## License
This project is licensed under the MIT License - see the LICENSE file for details.
