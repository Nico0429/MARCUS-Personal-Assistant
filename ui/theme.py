# ui/theme.py

CYAN_PRIMARY = "#00fbff"
CYAN_HOVER = "rgba(0, 251, 255, 50)"
BG_DARK_TRANSLUCENT = "rgba(10, 15, 20, 210)"
BORDER_DARK = "#004444"
TEXT_LIGHT = "#ffffff"
TEXT_MUTED = "#aaaaaa"
ALERT_RED = "#ff5555"
ALERT_HOVER = "rgba(255, 85, 85, 50)"

def get_master_stylesheet():
    return f"""
    /* --- MASTER HUD FRAMES --- */
    QFrame#HudFrame {{
        background-color: {BG_DARK_TRANSLUCENT};
        border: 1px solid {BORDER_DARK};
        border-radius: 8px;
    }}

    /* --- MASTER LABELS --- */
    QLabel {{
        background: transparent;
        border: none;
    }}
    QLabel#CyanSub {{ color: {CYAN_PRIMARY}; font-family: 'Consolas'; font-size: 11px; }}
    QLabel#WhiteTitle {{ color: {TEXT_LIGHT}; font-family: 'Consolas'; font-size: 14px; font-weight: bold; }}
    QLabel#TimerText {{ color: {TEXT_LIGHT}; font-family: 'Consolas'; font-size: 36px; font-weight: bold; }}
    QLabel#HeaderCyan {{ color: {CYAN_PRIMARY}; font-family: 'Consolas'; font-size: 13px; font-weight: bold; }}

    /* --- STANDARD ACTION BUTTONS --- */
    QPushButton {{
        background: transparent; 
        color: {CYAN_PRIMARY}; 
        border: 1px solid {CYAN_PRIMARY}; 
        border-radius: 4px; 
        font-family: 'Consolas';
        font-weight: bold; 
        padding: 4px 8px; /* Reduced side padding so buttons breathe naturally */
    }}
    QPushButton:hover {{ background: {CYAN_HOVER}; color: {TEXT_LIGHT}; }}

    /* --- ALERT BUTTONS (Like Cancel or [X]) --- */
    QPushButton[cssClass="alert"] {{
        color: {ALERT_RED}; 
        border: 1px solid {ALERT_RED}; 
        padding: 2px 5px; /* Tiny padding so [X] isn't crushed */
    }}
    QPushButton[cssClass="alert"]:hover {{ background: {ALERT_HOVER}; color: {TEXT_LIGHT}; }}

    /* --- BARE SEGON UI ICON BUTTONS --- */
    QPushButton[cssClass="icon_only"] {{
        border: none;
        color: {CYAN_PRIMARY};
        font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets";
        font-size: 14px;
        padding: 0px; /* CRITICAL: 0 padding so the icon fits */
    }}
    QPushButton[cssClass="icon_only"]:hover {{ background: rgba(0, 255, 204, 25); }}
    QPushButton[cssClass="icon_only"]:pressed {{ background: rgba(0, 0, 0, 150); color: #00ccaa; }}

    /* --- OS SYSTEM ICONS (Mic, Mute) --- */
    QPushButton[cssClass="os_icon"] {{
        background: transparent; 
        color: #888888; 
        border: 1px solid #444444; 
        border-radius: 4px; 
        font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets"; 
        font-size: 14px; 
        padding: 0px; /* CRITICAL: 0 padding */
    }}
    QPushButton[cssClass="os_icon"]:hover {{ background: rgba(255, 255, 255, 10); color: #aaaaaa; }}

    /* --- OS SYSTEM TEXT ICONS (The [-] Fold Button) --- */
    QPushButton[cssClass="os_text_icon"] {{
        background: transparent; 
        color: #888888; 
        border: 1px solid #444444; 
        border-radius: 4px; 
        font-family: 'Consolas';
        font-weight: bold;
        font-size: 12px; 
        padding: 0px; /* CRITICAL: 0 padding */
    }}
    QPushButton[cssClass="os_text_icon"]:hover {{ background: rgba(255, 255, 255, 10); color: #aaaaaa; }}

    /* --- APPLICATION ALERTS (MUTED STATES) --- */
    QPushButton[cssClass="os_icon_alert"] {{
        background: rgba(255, 50, 50, 40); 
        color: {ALERT_RED}; 
        border: 1px solid {ALERT_RED}; 
        border-radius: 4px; 
        font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets"; 
        font-size: 14px; 
        padding: 0px; /* CRITICAL: 0 padding */
    }}
    QPushButton[cssClass="os_icon_alert"]:hover {{ background: rgba(255, 50, 50, 60); }}

    /* --- CHAT FIELD ELEMENTS --- */
    QTextBrowser {{
        font-family: 'Consolas'; 
        font-size: 13px; 
        background: transparent; 
        color: #e0e0e0; 
        border: none;
        selection-background-color: {CYAN_PRIMARY}; 
        selection-color: #000000;
    }}
    QLineEdit {{
        font-family: 'Consolas'; 
        font-size: 11px;         /* <-- REDUCED FROM 13px */
        padding: 5px 8px;        /* <-- REDUCED VERTICAL PADDING (4px top/bottom, 8px sides) */
        background: rgba(0, 40, 40, 100); 
        color: {CYAN_PRIMARY}; 
        border: 1px solid {CYAN_PRIMARY}; 
        border-radius: 4px;
        selection-background-color: {CYAN_PRIMARY}; 
        selection-color: #000000;
    }}
    """