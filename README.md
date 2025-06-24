# Chess LLM Analyzer

A powerful Python tool for analyzing your Chess.com games using Stockfish (with hardware acceleration), OpenAI GPT-4, and a persistent database. Get actionable, AI-powered improvement suggestions based on your real mistakes.

---

## Features

- **Fetches all lost games** for a given year from Chess.com (using your username)
- **Analyzes every move** you played using the Stockfish chess engine (CPU-optimized, multi-core)
- **Caches all analysis** in a local SQLite database for instant re-analysis and cost savings
- **Identifies blunders, mistakes, inaccuracies** (with customizable thresholds)
- **Tracks color-specific (White/Black) and phase-specific (opening/middlegame/tactics) errors**
- **Aggregates your most common mistakes and error patterns**
- **Generates detailed, actionable improvement suggestions** using GPT-4.1
- **Produces a beautiful Markdown report** with stats, charts, and a study plan
- **Supports hardware acceleration** (multi-core CPU, and can be extended for GPU engines)
- **CLI prompts** for username, cleanup, and year selection

---

## Tech Stack

- **Python 3.8+**
- **Stockfish** (world-class chess engine, multi-core CPU acceleration)
- **OpenAI GPT-4.1** (for natural language explanations and improvement plans)
- **Chess.com API** (for fetching your games)
- **SQLite** (for persistent, fast, local caching of all analysis)
- **Multiprocessing** (for fast, parallel analysis of many games)

---

## Quick Setup Guide

### Step 1: Clone the Repository
```bash
git clone https://github.com/alcow5/chess-analyzer.git
cd chess-analyzer
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Install Stockfish Chess Engine
**Windows:**
1. Download from: https://stockfishchess.org/download/
2. Extract the `.exe` file to a folder (e.g., `C:\stockfish\`)
3. Add the folder to your system PATH, OR update the path in `analyze.py` line 15:
   ```python
   engine_path: str = r"C:\path\to\your\stockfish.exe"
   ```

**macOS:**
```bash
brew install stockfish
```

**Linux:**
```bash
sudo apt-get install stockfish
# or
sudo yum install stockfish
```

### Step 4: Get OpenAI API Key
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Go to "API Keys" section
4. Create a new API key
5. Copy the key (starts with `sk-`)

### Step 5: Create Environment File
Create a `.env` file in the project root:
```bash
# Windows
echo OPENAI_API_KEY=your_actual_api_key_here > .env

# macOS/Linux
echo "OPENAI_API_KEY=your_actual_api_key_here" > .env
```

**Important:** Replace `your_actual_api_key_here` with your real OpenAI API key.

### Step 6: Test the Setup
```bash
python improvement_suggestions.py
```

When prompted, enter your Chess.com username. The script will:
- Fetch your lost games from 2025
- Analyze them using Stockfish
- Generate improvement suggestions using GPT-4.1
- Save a detailed report in the `reports/` folder

---

## Prerequisites

1. **Stockfish Engine**
   - Download from: https://stockfishchess.org/download/
   - Add to your system PATH or specify the path in `analyze.py`

2. **OpenAI API Key**
   - Get from https://platform.openai.com/
   - Create a `.env` file in the project root:
     ```
     OPENAI_API_KEY=your_api_key_here
     ```

3. **Python dependencies**
   - Install with:
     ```bash
     pip install -r requirements.txt
     ```

---

## Usage

1. **Run the main script:**
   ```bash
   python improvement_suggestions.py
   ```

2. **Enter your Chess.com username** when prompted.
3. **The script will fetch all your lost games from 2025** (or any year you specify in the code).
4. **Analysis is cached**: Only new games are analyzed; old results are loaded instantly from the database.
5. **A detailed Markdown report** is generated in the `reports/` folder.
6. **You can clean up old analysis data** (older than 30 days) when prompted.

---

## How It Works

- **Game Fetching:** Uses the Chess.com public API to download all your lost games for a given year.
- **Move Analysis:** Each move you played is analyzed by Stockfish (using all available CPU cores for speed).
- **Database Caching:** All game analysis is stored in a local SQLite database. Re-running the script is instant for already-analyzed games.
- **Error Detection:** Blunders, mistakes, and inaccuracies are detected based on evaluation drops.
- **Color & Phase Analysis:** Errors are tracked by color (White/Black) and by game phase (opening, middlegame, tactics).
- **AI Suggestions:** The most common mistakes and patterns are summarized and sent to GPT-4.1 for actionable improvement advice.
- **Hardware Acceleration:** The script uses Python's multiprocessing to analyze many games in parallel, making full use of your CPU. (Can be extended for GPU engines like Leela Chess Zero.)

---

## Project Structure

- `improvement_suggestions.py` - Main entry point and report generator
- `fetch.py` - Chess.com API integration
- `analyze.py` - Stockfish analysis and blunder detection
- `explain.py` - GPT-4 integration for move explanations
- `database.py` - SQLite caching and analysis storage
- `utils.py` - Utility functions and environment loading
- `fix_analysis.py` - (Optional) Script to re-analyze all games if logic is updated
- `reports/` - Output Markdown reports
- `requirements.txt` - Python dependencies

---

## Example Output

- **Color-specific error breakdown** (White/Black)
- **Most common error moves**
- **Game phase analysis** (opening, middlegame, tactics)
- **AI-generated improvement plan** (with specific advice for your weaknesses)
- **Study plan for the next 2 weeks**

---

## Troubleshooting

**"Stockfish not found" error:**
- Make sure Stockfish is installed and in your PATH
- Or update the `engine_path` in `analyze.py` line 15

**"OPENAI_API_KEY not found" error:**
- Check that your `.env` file exists and contains the correct API key
- Make sure there are no spaces around the `=` sign

**"No games found" error:**
- Verify your Chess.com username is correct
- Check that you have played games in the specified year

**Slow analysis:**
- The first run analyzes all games and may take 10-30 minutes
- Subsequent runs use cached data and are much faster

---

## Notes

- Requires internet connection for Chess.com API and OpenAI API
- Stockfish must be installed and accessible via PATH
- OpenAI API usage incurs costs based on your plan
- All analysis is cached for speed and cost savings

---

## FAQ

**Q: How do I change the year or number of games analyzed?**
- Edit the call to `get_lost_games_from_year(api, username, YEAR)` in `improvement_suggestions.py`.

**Q: Can I use a GPU chess engine?**
- The script is optimized for multi-core CPU Stockfish, but can be extended to use Leela Chess Zero (GPU) with minor changes.

**Q: How do I re-analyze all games if I update the logic?**
- Run `python fix_analysis.py` to clear and re-analyze all games in the database.

**Q: How much does this cost?**
- Chess.com API: Free
- OpenAI API: ~$0.01-0.10 per analysis (depending on number of games)
- Stockfish: Free

---

## License

MIT License. See LICENSE file for details. 
