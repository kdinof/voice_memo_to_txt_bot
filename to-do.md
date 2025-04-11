Project: Telegram Voice Note Transcriber & Structurer Bot
Goal: Build a Telegram bot that receives voice notes (English/Russian), transcribes them using OpenAI Whisper, structures the text using an OpenAI LLM (like GPT-3.5/GPT-4), and sends the structured text back to the user.

Phase 1: Setup & Preparation
[ ] Task 1: Get Necessary API Keys

What: You need unique keys (like passwords) to let your code talk to Telegram and OpenAI services.

How:

Telegram: Chat with the BotFather bot on Telegram, use the /newbot command, and follow its instructions to get a TELEGRAM_BOT_TOKEN.

OpenAI: Create an account on the OpenAI website (https://openai.com/), go to the API keys section, and generate a new OPENAI_API_KEY.

Why: These keys authenticate your bot, proving it has permission to use the Telegram and OpenAI platforms. Keep them secret! Don't share them or put them directly in your code that gets pushed to public places like GitHub.

Tip: Save these keys somewhere secure for now. We'll handle them properly in Task 4.

[ ] Task 2: Set Up Your Development Environment

What: Prepare your computer for writing Python code for this project.

How:

Make sure you have Python installed (version 3.7 or newer is good). You can check by opening a terminal or command prompt and typing python --version or python3 --version.

Create a new folder (directory) for your project (e.g., telegram_transcriber_bot).

Navigate into that folder in your terminal (cd telegram_transcriber_bot).

Create a Python virtual environment: python -m venv venv (or python3 -m venv venv).

Activate the virtual environment:

Windows: .\venv\Scripts\activate

macOS/Linux: source venv/bin/activate
(You should see (venv) at the beginning of your terminal prompt).

Why: A virtual environment keeps the Python libraries (packages) for this project separate from other projects or your system's Python, preventing conflicts.

[ ] Task 3: Install Required Python Libraries

What: Install the tools (libraries) your Python code will need to interact with Telegram, OpenAI, and manage settings.

How: With your virtual environment active, run these commands in your terminal:

pip install python-telegram-bot --upgrade
pip install openai --upgrade
pip install python-dotenv --upgrade

Why:

python-telegram-bot: Makes it much easier to handle Telegram bot features (receiving messages, sending replies, etc.).

openai: Provides a convenient way to use the OpenAI API (for both Whisper transcription and GPT structuring).

python-dotenv: Helps load your secret API keys securely from a file instead of writing them directly in your code.

[ ] Task 4: Securely Store API Keys

What: Create a special file to hold your secret API keys, which your code can read without exposing the keys in the main script.

How:

In your project folder, create a file named exactly .env (starts with a dot).

Add your keys to this file like this:

TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_TELEGRAM_TOKEN_HERE
OPENAI_API_KEY=YOUR_ACTUAL_OPENAI_KEY_HERE

(Very Important!) Create another file named .gitignore in your project folder and add .env and venv/ to it on separate lines. This tells Git (version control) to ignore these files so you don't accidentally commit your secrets or the whole virtual environment.

Why: This is crucial for security. It keeps your secret keys out of your main codebase and prevents accidental sharing.

Phase 2: Basic Bot Implementation
[ ] Task 5: Create the Basic Bot Script (bot.py)

What: Start writing the main Python file for your bot. Set up basic imports, load API keys from the .env file, and configure logging.

How:

Create a file named bot.py in your project folder.

Import necessary modules (os, logging, load_dotenv, telegram.ext, openai).

Use load_dotenv() to load the variables from your .env file.

Get the keys into Python variables using os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("OPENAI_API_KEY").

Set up basic logging using the logging module (helps see what the bot is doing and diagnose issues).

Configure the OpenAI client using openai.api_key = YOUR_OPENAI_KEY_VARIABLE.

Why: This sets up the foundation of your script, making API keys available and enabling useful logging for debugging.

[ ] Task 6: Implement Start & Help Commands

What: Add basic commands like /start and /help so users know how to interact with your bot.

How:

Define asynchronous functions (using async def) for start and help. These functions take update: Update and context: ContextTypes.DEFAULT_TYPE as arguments.

Inside these functions, use await update.message.reply_text("Your message here") to send a reply.

In the main part of your script (e.g., inside a main() function), create a telegram.ext.Application instance using your Telegram token.

Create CommandHandler instances for "start" and "help", linking them to your start and help functions.

Add these handlers to the application using application.add_handler().

Start the bot using application.run_polling().

Why: These commands provide a basic interface for users and are standard practice for Telegram bots. run_polling starts the bot listening for messages.

Phase 3: Core Functionality - Voice Processing
[ ] Task 7: Handle Incoming Voice Messages

What: Make the bot recognize when a user sends a voice message.

How:

Define a new async def function (e.g., handle_voice_message) that takes update and context.

Create a MessageHandler. Use filters.VOICE to specify that this handler should only react to voice messages. Link it to your handle_voice_message function.

Add this MessageHandler to your application using application.add_handler().

Inside handle_voice_message, you can access the voice message details via update.message.voice.

Why: This is the entry point for your bot's main feature – reacting specifically when it receives audio.

[ ] Task 8: Download the Voice File

What: Get the actual audio file sent by the user from Telegram's servers onto the machine where your bot script is running.

How:

Inside handle_voice_message, get the file_id from update.message.voice.file_id.

Use voice_file_info = await context.bot.get_file(file_id) to get information about the file, including its download path.

Use tempfile.NamedTemporaryFile to create a temporary file (e.g., with a .ogg suffix, as Telegram often uses Opus audio in an OGG container). This avoids cluttering your server.

Use await voice_file_info.download_to_drive(custom_path=temp_audio_file.name) to save the audio to that temporary file. Store the file path.

(Crucial!) Use a try...finally block to ensure the temporary file is always deleted afterwards (using os.remove(audio_file_path)) even if errors occur later.

Why: You need the actual audio data as a file to send it to the OpenAI Whisper API for transcription. Using temporary files keeps things tidy.

[ ] Task 9: Transcribe Audio using OpenAI Whisper

What: Send the downloaded audio file to OpenAI's Whisper API and get the transcribed text back.

How:

Inside handle_voice_message (after downloading the file), open the temporary audio file in binary read mode ("rb").

Call the OpenAI Whisper API: transcript_response = openai.audio.transcriptions.create(model="whisper-1", file=audio_file_object). (Use await if using the async version of the OpenAI library, otherwise the standard sync call is fine inside an async def function for I/O).

Extract the transcribed text from the response (usually transcript_response.text).

Wrap this API call in a try...except block to catch potential errors (e.g., network issues, OpenAI API errors). Log any errors.

Why: This converts the spoken words in the audio file into written text, which is the first major step in processing the user's input.

[ ] Task 10: Structure Text using OpenAI Chat Completions

What: Send the raw transcribed text to an OpenAI chat model (like GPT-3.5-turbo or GPT-4) with instructions (a prompt) on how to structure it.

How:

Inside handle_voice_message (after getting the raw transcript), define your structuring prompt. This is a string telling the AI what you want it to do (e.g., "Summarize the key points from the following text using bullet points: [raw_text]"). Include the raw_text variable in your prompt.

Call the OpenAI Chat Completions API: completion_response = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[...]).

The messages list should contain at least a system message (optional, sets the AI's role) and a user message containing your prompt.

Extract the structured text from the response (usually completion_response.choices[0].message.content).

Wrap this in a try...except block for error handling.

Why: This uses the power of a Large Language Model (LLM) to organize the potentially messy raw transcription into a more readable and useful format according to your instructions.

[ ] Task 11: Send Structured Text Back to User

What: Send the final, structured text back to the user in the Telegram chat.

How:

Inside handle_voice_message, after getting the structured text, use await update.message.reply_text(structured_text, parse_mode='Markdown').

Using parse_mode='Markdown' allows you to use simple formatting like *bold*, _italic_, and bullet points (* item or - item) generated by the structuring step.

Wrap this in a try...except block in case sending fails.

Why: This completes the core loop – the user sent voice, and they receive the processed, structured text back.

Phase 4: Refinement & Deployment
[ ] Task 12: Add User Feedback & Improve Error Handling

What: Make the bot feel more responsive and handle problems gracefully.

How:

Feedback: Before long operations (download, transcribe, structure), send a temporary message like "Processing..." using await update.message.reply_text(...) and save the returned message object. Then, use await context.bot.edit_message_text(...) to update that same message (e.g., "Transcribing...", "Structuring..."). Finally, delete the status message using await context.bot.delete_message(...) before sending the final result. You can also use await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing').

Error Handling: Make your try...except blocks more specific if possible. Catch common errors from python-telegram-bot or openai. When an error occurs, log it clearly and send a helpful message to the user (e.g., "Sorry, I couldn't transcribe that. Please try again." or "Sorry, an error occurred while structuring the text.").

Why: Good feedback makes the bot less confusing, and robust error handling prevents crashes and informs the user when things go wrong.

[ ] Task 13: Prepare for Deployment

What: Get your code ready to run on a server instead of just your local computer.

How:

Freeze Dependencies: Make sure your virtual environment is active and run pip freeze > requirements.txt. This creates a list of all the libraries your project needs, which the server will use for installation.

Review Code: Ensure no secret keys are hardcoded. Double-check that API keys are loaded from environment variables.

(If using Heroku): Create a file named Procfile (no extension) and add worker: python bot.py to it. This tells Heroku how to run your bot.

Why: Deployment requires specific configuration files (requirements.txt, maybe Procfile) and ensuring your code relies on environment variables for secrets, as you'll configure those differently on the server.

[ ] Task 14: Choose Hosting & Deploy

What: Select a platform to host your bot (so it runs 24/7) and upload/configure your code there.

How:

Choose: Options include Heroku (often good for starting), PythonAnywhere, Render, Google Cloud (App Engine/Cloud Run), AWS (EC2/Elastic Beanstalk/Lambda), or a basic VPS. Research their free/hobby tiers and deployment methods.

Configure Environment Variables: On your chosen platform, find the settings section to add your TELEGRAM_BOT_TOKEN and OPENAI_API_KEY as environment variables.

Deploy: Follow the specific instructions provided by your hosting platform to upload your code (usually via Git or a web interface) and start the bot process (often involves installing dependencies from requirements.txt and running python bot.py).

Why: Your bot needs to run continuously on a server to be available to users in Telegram. Local testing only keeps it running while your computer is on and the script is active.

[ ] Task 15: Test Thoroughly on Server

What: After deploying, test all features again to ensure everything works correctly in the live environment.

How: Send various voice notes (English, Russian, short, long, quiet, noisy) to your deployed bot. Check if it handles errors as expected. Check the logs on your hosting platform for any issues.

Why: The server environment might differ slightly from your local setup, so testing after deployment is crucial to catch any new problems.

Phase 4: Remote Server Deployment
[ ] Task 1: Choose a Server Provider
What: Select a cloud server provider for hosting your bot.

Options:
- DigitalOcean (Recommended for beginners)
- AWS EC2
- Google Cloud Platform
- Linode
- Vultr

How:
1. Sign up for an account with your chosen provider
2. Create a new virtual machine (droplet/instance)
3. Recommended specs:
   - 1GB RAM minimum
   - 25GB SSD storage
   - Ubuntu 22.04 LTS

[ ] Task 2: Server Initial Setup
What: Configure your server with necessary security and software.

How:
1. SSH into your server: `ssh root@your_server_ip`
2. Create a new user: 
   ```bash
   adduser botuser
   usermod -aG sudo botuser
   ```
3. Set up SSH keys for the new user
4. Install required system packages:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv git ffmpeg
   ```

[ ] Task 3: Deploy the Bot
What: Transfer and set up your bot on the server.

How:
1. Clone your repository:
   ```bash
   git clone https://github.com/kdinof/voice_memo_to_txt_bot.git
   cd voice_memo_to_txt_bot
   ```
2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create .env file with your API keys
5. Test the bot:
   ```bash
   python bot.py
   ```

[ ] Task 4: Set Up Process Management
What: Ensure the bot runs continuously and restarts automatically.

How:
1. Install PM2 (Node.js process manager):
   ```bash
   sudo npm install -g pm2
   ```
2. Create a PM2 configuration file (ecosystem.config.js):
   ```javascript
   module.exports = {
     apps: [{
       name: "voice-bot",
       script: "python",
       args: "bot.py",
       interpreter: "venv/bin/python",
       env: {
         PYTHONUNBUFFERED: "1"
       }
     }]
   }
   ```
3. Start the bot with PM2:
   ```bash
   pm2 start ecosystem.config.js
   ```
4. Set up PM2 to start on boot:
   ```bash
   pm2 startup
   pm2 save
   ```

[ ] Task 5: Set Up Monitoring
What: Monitor your bot's performance and logs.

How:
1. Install monitoring tools:
   ```bash
   sudo apt install -y htop
   ```
2. Monitor logs:
   ```bash
   pm2 logs voice-bot
   ```
3. Set up basic monitoring:
   ```bash
   pm2 monit
   ```

[ ] Task 6: Security Hardening
What: Secure your server and bot.

How:
1. Set up a firewall:
   ```bash
   sudo ufw allow ssh
   sudo ufw allow http
   sudo ufw allow https
   sudo ufw enable
   ```
2. Install fail2ban:
   ```bash
   sudo apt install -y fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```
3. Set up automatic security updates:
   ```bash
   sudo apt install -y unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

[ ] Task 7: Backup Strategy
What: Implement a backup system for your bot's data and configuration.

How:
1. Create a backup script:
   ```bash
   #!/bin/bash
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   BACKUP_DIR="/path/to/backups"
   mkdir -p $BACKUP_DIR
   tar -czf $BACKUP_DIR/bot_backup_$TIMESTAMP.tar.gz /path/to/bot
   ```
2. Set up automated backups:
   ```bash
   sudo crontab -e
   # Add: 0 0 * * * /path/to/backup_script.sh
   ```

[ ] Task 8: SSL/TLS Setup (Optional)
What: Secure your bot's communications with SSL/TLS.

How:
1. Install Certbot:
   ```bash
   sudo apt install -y certbot
   ```
2. Obtain SSL certificate:
   ```bash
   sudo certbot certonly --standalone -d your-domain.com
   ```
3. Set up automatic renewal:
   ```bash
   sudo certbot renew --dry-run
   ```

Remember to:
- Keep your .env file secure and never commit it to version control
- Regularly update your system and Python packages
- Monitor your bot's performance and logs
- Set up alerts for any issues
- Keep backups of your configuration and data