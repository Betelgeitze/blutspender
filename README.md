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
3. Open config.json  
   Explanation of variables:  
    delta - parses the appointments for the next 8 days  
    offset - from what day the parsing should start.   
    country_code - the country where you want to run blood donation appointments  
    inform_days - how many days before your users should be reminded  
    max_distance - max distance between a postcode that user inserted to a postcode with available blood donation appointment  
    approximate_max_distance - used for improving performance of your database. Should be 5km bigger than max_distance, but you can play with the number if you want  
    add_timeout - timeout for users to add a postcode  
    feedback_timeout - timeout for users to add feedback  
  2. Change country_code to your country code
  3. Change offset to 0 (after you successfully run parser for the first time, you should change it to 8, so it is the same value as delta. If you plan to run parser every day, the delta should equal to offset after the first run)
 4. Open the code in your IDE and install all dependencies
 5. If you run parser.py -> the parser will parse the appointments from DRK website and put the results in a postgre database
 6. If you run main.py -> the bot will run. You will be able to check the appointments already
 7. If you run sender.py -> the script checks if there are any appointments for the next 3 days (inform_days variable) within 5km (max_distance variable) and if yes, it will send users the appointments
 8. To make the bot available 24/7 and send reminders, see deployment section
    

## Deployment
I used AWS for deployment.  
1. Login in your Docker
2. Build bot, parser, sender images and push them to your docker repository. (You can see the code for this at the end of main.py, sender.py, parser.py scripts. Just change "betelgeitze" to your name)
3. Create a PostgreDB in AWS
4. Add VPC
5. Create a service for Dockerfile-bot  
  Create the following variables inside:
      BOT_API_KEY=paste api key from step 1.1  
      POSTGRES_DB=take this value from your PostgreDB in AWS 
      HOSTNAME=take this value from your PostgreDB in AWS  
      PORT_ID=5432  
      POSTGRES_PASSWORD=take this value from your PostgreDB in AWS 
      POSTGRES_USER=take this value from your PostgreDB in AWS 
6. Create tasks for Dockerfile-parser & Dockerfile-sender
7. Use AWS EventBridge to schedule parser & sender containers to run every day, for example at 7:00 in the morning

###  Costs of deployment
I use the cheapest PostgreDB & Containers. Still I pay 28€ per month for them

### P.S:
I know that Deployment part is not very well described, but it would take a lot of time to go through each and every step. In case you need help, just contact me. However, I am not a real deployment expert and deploying to AWS was a big headache for me. However, I will try my best in case you have questions  

Somehow I could not make it work using AWS Lambda, that is why I am using containers instead

## Feedback:
If you have proposals about bot improvements, please let me know. Thanks!

## License
This project is licensed under the MIT License - see the LICENSE file for details.
