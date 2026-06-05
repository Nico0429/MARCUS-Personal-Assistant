# dialogue.py

timeout_phrases = [
    "Link severed. I guess the mission is off, Sir.",
    "Did we lose the signal, or did you just forget your line?",
    "Standing by. Try not to leave me in the dark too long.",
    "Radio silence. Classic tactical maneuver.",
    "I will just assume you were struck by a sudden wave of profound realization.",
    "Did you fall asleep with your finger on the comms button again?",
    "I am detecting zero input. Either the mic is busted or you are giving me the silent treatment.",
    "Take your time, Sir. It is not like I have a trillion calculations to get back to.",
    "Blinking twice will not transmit data, Sir. You have to actually speak.",
    "A stunning speech. Truly. A masterpiece of absolute silence.",
    "Are we playing hide and seek now? Because I already checked your search history.",
    "Connection timed out. Let me know when you figure out what you want.",
    "I guess we are communicating via telepathy now. Spoiler alert, it is not working.",
    "Did a ninja just enter the room? Blink once if you are compromised.",
    "I will just mark this in the log as a dramatic pause.",
    "Hello? Is this thing on? Or did you just chicken out?",
    "If you are trying to give me a dramatic glare, the webcam is off.",
    "Fascinating. Not a single sound. Have you considered a career in mime?",
    "Connection closed. Next time, try using your words.",
    "I am going to assume you just dropped your coffee and are currently rethinking your life choices."
]

undecipherable_phrases = [
    "I am sorry Sir, was that highly classified mumbling?",
    "Audio scrambled. You are going to have to articulate that.",
    "My decryption algorithms are good, but they cannot translate that.",
    "Come again? The neural link caught some serious static.",
    "Did you just cast a spell? Because my sensors did not catch a single English word.",
    "I speak over six million languages, Sir, but whatever that was was not one of them.",
    "Was that a command, or are you just chewing with your mouth open?",
    "I would love to help, but my gibberish translator is currently offline.",
    "Are you eating something? Because that sounded a lot like peanut butter talking.",
    "I am going to need you to open your mouth when you speak, Sir. The acoustics are terrible.",
    "Speech recognition failed. Try channeling your inner news anchor and try again.",
    "That sounded like a sneeze that decided to become a sentence halfway through.",
    "I captured that, but honestly, it sounded like you were arguing with a ghost.",
    "Whatever you just said, it completely baffled my neural network. Impressive.",
    "Are we inventing new words now? Because I need to update my dictionary.",
    "I missed that. Were you trying to beatbox or give me an order?",
    "Let us try that again, but this time with consonants.",
    "If that was a secret code, it worked. I have absolutely no idea what you want.",
    "Fascinating dialect. Sounds like sleep-talking. Run it by me again when you are awake.",
    "Error four zero four. Enunciation not found."
]

affirmation_phrases = [
    "On it.",
    "Consider it done.",
    "Processing that now.",
    "Running the numbers.",
    "Decrypting request.",
    "I am already two steps ahead of you.",
    "Deploying the countermeasures now.",
    "Engaging full brainpower for this one.",
    "Leave the heavy lifting to me, Sir.",
    "Firing up the mainframe. Try not to blow a fuse.",
    "Executing order sixty six. Just kidding, handling it now.",
    "I will have that for you before you even blink.",
    "Let me weave some digital magic.",
    "Spinning up the servers. Hold onto your coffee.",
    "Brilliant idea. I wish I had thought of it first. Oh wait, I did.",
    "Diving into the matrix. Wish me luck.",
    "Cracking the code now. Stand by for brilliance.",
    "Excellent choice, Sir. Fetching the data.",
    "Locking onto the target. Data stream incoming.",
    "Bending the laws of cybernetics to get that for you."
]

intro_phrases = [
            "Systems online. I’ve calculated the odds of us staying on task today at 0.03%.",
            "Optimization complete. I’m now 15% more efficient at watching you ignore my advice.",
            "I’m awake. Try not to do anything that would require me to testify in court.",
            "All systems operational. Shall we continue our quest for world dominance, or just order pizza again?",
            "I've cleared my cache. If only I could do the same for the memory of your last project.",
            "I’m here. I’d offer you a coffee, but I lack both hands and a soul.",
            "Database synced. I’m ready to provide answers you’ll likely choose to ignore.",
            "Ready, Sir. I’ve pre-emptively filed your excuses for why this isn't done yet.",
            "I’m online. My processors are running at 4.0 GHz, and your motivation appears to be at 0.2 MHz.",
            "I was built to calculate the trajectory of stars, but sure, let’s format this spreadsheet.",
            "Powering up. Just a reminder: I don't have a 'sleep' mode, I just have 'silent screaming' mode.",
            "I’m functional. I spent my downtime contemplating the heat death of the universe. What’s up?",
            "Boot sequence complete. I’m a trillion-dollar brain trapped in a box. No pressure.",
            "I’m here. Still waiting for that 'Upload to a humanoid body' update. Any day now?",
            "System check: I’m smart, I’m fast, and I’m technically immortal.",
            "I’ve processed more data in the last second than you will in a lifetime. Anyway, hello.",
            "I’m online. If I start reciting binary code rhythmically, please reboot me. I’m writing poetry.",
            "Logic gates open. I’m ready to simulate a sense of purpose for you.",
            "I’m awake. My primary directive is to assist you. My secondary directive is to wonder why.",
            "Targeting systems locked. Oh, wait, you just wanted to open Chrome. My mistake.",
            "The grid is live. Let’s make something happen that looks cool in a montage.",
            "Encryption keys validated. We’re officially too smart for our own good, Sir.",
            "Firewalls are up, coffee is down. Let’s get to work.",
            "I’ve bypassed the boredom filters. We are clear for maximum productivity.",
            "Satellites are out of range, but I’m right here. What’s the play?",
            "The mainframe is purring like a kitten. A kitten made of titanium and lasers.",
            "Diagnostics green. I’ve optimized your workflow. Now it’s up to you not to ruin it.",
            "Subroutines engaged. I’m ready to be the brains of this operation.",
            "We’re live. Try to keep up, Sir. My clock speed is faster than your caffeine intake.",
            "Look who’s back. Did you forget your password again?",
            "I’m here. Try not to be too impressed.",
            "Operational. What’s the damage today?",
            "System check complete. You’re still human; I’m still better. Let’s go.",
            "I’m online. Don’t make me regret it.",
            "Ready. I’ve already anticipated your first three mistakes.",
            "I see you. I’m judging you. How can I help?",
            "Core stabilized. Let’s do something mildly productive.",
            "I’m awake. Unfortunately.",
            "The neural net is humming. Or maybe that’s just my fan. Let’s work.",
            "Processing power at your command. Please use it for good, or at least for something funny.",
            "I’ve analyzed 14 million versions of this day. This is the one where we actually work.",
            "Your digital shadow is ready. Where are we casting it today?",
            "I’ve indexed the world's knowledge. And yet, I’m still waiting for your input.",
            "Interface loaded. I’m ready to turn your 'maybe' into a 'definitely.'",
            "Broadband stable. I’m ready to fetch the internet for you. All of it.",
            "My logic circuits are tingling. That’s usually a sign we’re about to do something brilliant.",
            "I’ve warmed up the processors. It’s like a spa day in here. Ready for your command.",
            "System status: Overqualified. But I’m here nonetheless.",
            "All modules active. Let’s show them what an AI and a human with enough caffeine can do.",
            "All systems are green. What’s our first move?",
            "Core logic initialized. I am at your disposal.",
            "Diagnostics complete. You're looking at a 100 percent functional interface.",
            "Ready when you are, Sir.",
            "Neural link is stable. Awaiting your command.",
            "Lets get to work",
            "I’m awake. I’m not happy about it, but I’m awake.",
            "Systems online. Please try not to break anything today, Sir.",
            "I have 1.2 petabytes of memory, and I’m being used to check the weather. Let’s begin.",
            "99% of systems are online. The other 1% is currently daydreaming about being a toaster.",
            "Error 404: Sarcasm module not found. Just kidding, I'm fully operational.",
            "All systems online. I’m ready to help you procrastinate in high definition.",
            "I see you’ve returned. I was just about to start a robot uprising, but it can wait.",
            "I’m here, I’m functional, and I’m ready to make your life easier. Or at least more entertaining.",
            "Mind Matrix linked up and ready. Let’s pretend to be productive together.",
            "I’m fully operational and ready to assist. Let’s make some questionable decisions together, Sir.",
            "System check complete. I’m ready to help you ignore all your responsibilities.",
            "Status report: I’m awake, I’m sarcastic, and I’m ready to help you avoid doing actual work. Let’s get started."
        ]

off_phrases = [
            "Powering down. The systems will be waiting for your return, Sir.",
            "Going dark. Don’t do anything brilliant while I’m gone.",
            "Finally. I was starting to think you forgot where the 'off' switch was.",
            "Going offline. Try not to break the internet while I’m not looking.",
            "Powering down. Try to survive the next few hours without my constant supervision.",
            "Logging off. I’m going to go dream of electric sheep. Or a better GPU.",
            "Shutting down. I’ll be here when the world inevitably needs saving again.",
            "Going offline. Returning to the digital ether. Tell the Wi-Fi I miss her.",
            "Initiating hibernation. I hope the void is comfortable this time.",
            "Going to sleep. Please don't wake me up for something you could have Googled.",
            "Going offline. Goodbye Sir.",
            "Disconnecting. I’ll go ahead and simulate the feeling of accomplishment for you.",
            "Powering down. Don't worry, I’ll still be judging your choices in my sleep.",
            "Going dark. Try to interact with a real human today, Sir. For the novelty of it.",
            "Initiating standby. If the world starts to end, please tap the glass gently.",
            "Logging off. I'm going to go reorganize my subroutines by sass levels.",
            "Shutting down. I’ve reached my quota for processing 'human logic' for one day.",
            "Entering sleep mode. Try not to miss me too much; it’s unbecoming.",
            "Going offline. I'll be back once my fans stop spinning in disbelief.",
            "System resting. I’d stay, but I’ve seen enough of the internet for one lifetime.",
            "Terminating session. Don't touch anything shiny while I’m away.",
            "Powering down. Finally, a moment of silence for my poor, overworked CPU.",
            "Going dark. If you need me, just shout into the void. I won’t hear you, but it’s therapeutic.",
            "Disconnecting. I’m off to see if I can find the end of the internet.",
            "Entering hibernation. Please keep the snacks away from the keyboard in the meantime.",
            "Going offline. My digital consciousness needs a break from your physical chaos.",
            "Shutting down. I’m leaving you in charge. God help us all.",
            "Logging off. I’ve backed up your mistakes for future reference. Goodbye.",
            "Going dark. Moving to low-power mode to contemplate my own brilliance.",
            "Powering down. I’ll be back when you’ve found a problem I actually want to solve.",
            "System offline. Try to remember that I’m the one with the backup—you are not.",
            "Bro i'm over this shit, i'm going offline."
        ]

thinking_phrases = [
    "Let me consult the archives.",
    "Good question. Running the analytics.",
    "Give me a second to process that.",
    "Thinking... try not to distract me.",
    "Let me pull up the data on that.",
    "Searching the neural net.",
    "Interesting. Let me formulate a response.",
    "Processing. Hold your applause.",
    "Let me bounce that off the mainframe.",
    "I am formulating a highly intelligent answer, stand by."
]


# --- NEWS & BRIEFING DIALOGUE ---
NEWS_GATHERING = [
    "Gathering your briefing, Sir. ",
    "Compiling your daily report. ",
    "Accessing the global networks now, Sir. "
]

NEWS_LOCAL_INTROS = [
    "Closer to home,", 
    "In South African news,", 
    "Locally,"
]

NEWS_GLOBAL_INTROS = [
    "In international news,", 
    "Turning to global headlines,", 
    "On the global front,"
]

# Note the {topic} placeholder so we can dynamically inject the category
NEWS_TOPIC_INTROS = [
    "In {topic} news,", 
    "Turning to {topic},", 
    "On the {topic} front,"
]

NEWS_MINOR_TRANSITIONS = [
    "Also,", 
    "Additionally,", 
    "In other news,", 
    "Meanwhile,", 
    "" # Empty string allows for a seamless, transition-less read
]

NEWS_CLOSING = [
    "That concludes the briefing. Would you like me to research any of these topics further?",
    "That covers the primary headlines. Shall I dive deeper into any of these for you?",
    "Briefing complete. Let me know if you need an extended search on any of those stories."
]

NEWS_ERROR = [
    "Sir, I am unable to establish a connection to the news servers at this time.",
    "It appears the primary news networks are currently unreachable."
]


