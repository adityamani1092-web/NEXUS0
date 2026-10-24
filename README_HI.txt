NEXUS PREMIUM BOT — AI IMAGE GENERATION UPDATE

FILES
- bot.py: Telegram bot source, including /imagine and /image commands
- db.py: existing bot database functions
- requirements.txt: Python dependencies
- .env.example: sample environment configuration (no secrets)
- existing banner/couple images

SETUP (Windows / Linux hosting)
1. Use Python 3.10 or newer.
2. Extract all ZIP files into one folder. Keep bot.py and db.py together.
3. Install dependencies:
   python -m pip install -r requirements.txt
4. Create your own .env from .env.example, or add the same values in your hosting Secrets / Environment Variables.
5. Set BOT_TOKEN and OWNER_ID for the existing bot. Add OPENAI_API_KEY for image generation.
6. Restart the bot process:
   python bot.py

GROUP IMAGE COMMANDS
/imagine a futuristic city at night
/image ek cute robot neon galaxy mein

You can also reply to a text message with /imagine (without a prompt) to use that text as the prompt. The bot replies with the generated image in the same chat.

IMAGE CONFIGURATION
OPENAI_API_KEY=your_actual_api_key
IMAGE_MODEL=gpt-image-2.5-flare
IMAGE_COOLDOWN_SECONDS=30
IMAGE_DAILY_LIMIT=10
IMAGE_QUALITY=medium

Create an API key at https://platform.openai.com/api-keys. The API key must have access to image generation, and your API account may need billing/credits enabled. Image generation is paid usage; check current pricing before enabling it for a group. Never post your API key in Telegram or share your .env file.

TELEGRAM CHECKS
- Add the bot to the group.
- Make sure it is not blocked and has permission to send messages/photos.
- Commands such as /imagine should be sent as a bot command in the group.
- If image generation fails, check the hosting console for the short error log and verify API key, model access, billing, and network access.

LIMITATIONS
- Cooldown and daily limits are in-memory and reset when the bot restarts.
- This package has been syntax-checked and ZIP integrity-checked, but it has not been live-tested with your private Telegram token or OpenAI API key.
- The bot cannot generate images until you supply your own valid OPENAI_API_KEY.

SECURITY
Never share BOT_TOKEN, OPENAI_API_KEY, database credentials, or your private .env file.
