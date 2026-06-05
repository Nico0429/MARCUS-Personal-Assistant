"""
================================================================================
FILE: triggers.py
ROLE: The Linguistic Lexicon & Scrubbers
================================================================================
Because intent classification is now handled dynamically by the Semantic Router, 
this file acts purely as a text-scrubbing lexicon. It strips out conversational 
filler so APIs only receive clean nouns and verbs.
================================================================================
"""

# ==========================================
# 1. HARD SYSTEM OVERRIDES 
# ==========================================
EXIT_PHRASES = [
    "exit", "shut down", "go to sleep", "goodbye", "offline", 
    "goodnight", "shut up", "cheers", "see you", "stop listening", "go to bed", "bye"
]

NEWS_OPT_IN = [
    "yes", "sure", "okay", "alright", "go ahead", "do it", 
    "read them", "tell me", "why not", "sounds good"
]

# ==========================================
# 2. NEWS TOPIC CLASSIFIERS
# ==========================================
NEWS_TECH = ["tech", "technology", "software", "hardware"]
NEWS_SPORT = ["sport", "sports", "football", "rugby", "cricket"]
NEWS_BUSINESS = ["business", "market", "finance", "economy", "stocks"]
NEWS_SCIENCE = ["science", "space", "physics"]
NEWS_HEALTH = ["health", "medical", "medicine"]
NEWS_ENTERTAINMENT = ["entertainment", "movies", "hollywood", "celebrity"]

# ==========================================
# 3. API TEXT SCRUBBERS (Removes conversational fluff)
# ==========================================
CONVERSATIONAL_FILLER = [
    "could you ", "can you ", "please ", "and call it ", "call it ", 
    "and name it ", "name it ", "called ", "set it to be ", "set it to ", 
    "make it be ", "make it ", "to be ", "with ", "add a new task ", 
    "add a task ", "add task ", "add ", "create a new task ", 
    "create a task ", "create task ", "create ", "new task "
]

# Notion Task Scrubbers
PRIORITY_KEYWORDS = ["priority", "high", "medium", "low"]
PRIORITY_SCRUBBER_PHRASES = [
    "high priority", "medium priority", "low priority",
    "make it high", "make it medium", "make it low",
    "set it to high", "set it to medium", "set it to low"
]

# Notion Shopping Scrubbers
SHOPPING_ADD_TRIGGERS = [
    "add to shopping list", "buy some", "we need to buy", 
    "add to groceries", "add to the grocery list", "we need some"
]

# Web Search Scrubbers
WEB_SEARCH_SCRUBBERS = [
    "Marcus", "can you", "please", "search for", "search", 
    "look up", "find out", "google", "check the internet for",
    "tell me", "what is the", "who is the"
]