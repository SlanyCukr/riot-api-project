# Tech Stack
- Pure Python heuristics
- Confidence scoring (0-100 scale)
- Weighted average combination
- Structured logging with metrics

# Project Structure
- `win_rate.py` - High win rate detection
- `rank_progression.py` - Account age vs rank analysis
- `performance.py` - KDA and performance consistency

# Commands
- Register in SmurfDetectionService
- Test with unit tests and real data
- Monitor via detection API endpoints

# Code Style
- Implement calculate_confidence() method
- Return float between 0 and 100
- Log key metrics for debugging
- Handle edge cases gracefully

# Do Not
- Don't return scores > 100 (cap with min())
- Don't ignore empty matches list
- Don't use magic numbers (define constants)
- Don't make algorithms too complex
