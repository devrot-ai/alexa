# FreshKeep — Your Kitchen Memory for Alexa

FreshKeep remembers what is in your kitchen. You tell Alexa what you bought, and it tracks expiration dates, warns you before food goes bad, and suggests meals using what is about to expire.

Built for the Amazon Developer Hackathon 2026.

## Why It Exists

Most households throw away about $1,500 of food a year. Not because people do not care, but because nobody wants to maintain a pantry app while carrying grocery bags. Voice is the answer, but Alexa needed a way to actually remember things. FreshKeep gives it that memory.

## Try It

Tell Alexa:

"We just bought spinach, yogurt, and chicken that expires in two days."

Then ask:

"What needs rescuing?"

It tells you what is about to go bad and how much money is at risk. Ask it to plan a rescue meal and it suggests something like a veggie omelette that uses up the expiring items. You can even paste a receipt and it will read the items for you.

## Getting Started

No cloud account needed. Just two terminals:

```bash
pip install -r requirements.txt

# Terminal 1 — start the server
python -m freshkeep.mcpserver

# Terminal 2 — start the web interface
python -m freshkeep.simulator.app
```

Open http://localhost:8800 in your browser, accept the consent prompt, and start talking to it.

## How It Works

The web interface sends your words to the server. The server figures out what you mean and calls the right tool — track items, check expiration, plan a meal, update the shopping list. Everything runs locally by default with a simple JSON file for storage. You can optionally use DynamoDB or Amazon Bedrock for more advanced features.

## Configuration

Copy `.env.example` to `.env` and change what you need. The defaults work fine for local use. Key settings include the server ports, storage type (JSON or DynamoDB), and whether to enable Bedrock or Textract.

## Privacy

Nothing is saved until you say yes. Deleting your data takes two steps so it cannot happen by accident. Your words are never stored in logs. The AI never makes decisions on its own — it only calls tools that have been checked and approved.

## Project Structure

The `freshkeep/` folder has all the Python code. The `tests/` folder has 34 tests. The `docs/` folder has architecture and security details. The `skill/` folder has the Alexa skill definition.

## License

MIT
