"""Keyword and signal tables for the Dispatch rules engine.

The engine is intentionally transparent: every classification can be traced back
to the concrete phrases below. Each ``case_type`` owns a list of
``(pattern, weight)`` pairs. Matching is case-insensitive; English single words
match on word boundaries, while phrases and Bangla (bn) tokens match as
substrings (see ``app.classifier._matches``).

Bangla and "mixed" locale support is first-class: bKash customers frequently
write in Bangla or Banglish, so the most common Bangla phrases are included
inline next to their English counterparts.
"""

# --------------------------------------------------------------------------- #
# case_type signals
# --------------------------------------------------------------------------- #
# Order of the dict does not decide ties — see PRIORITY in app.classifier.
CASE_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    # Fraud / social engineering carries the strongest weights so a genuine
    # phishing signal wins even when other categories are also mentioned.
    "phishing_or_social_engineering": [
        ("otp", 5),
        ("one time password", 5),
        ("one-time password", 5),
        ("pin", 4),
        ("password", 4),
        ("passcode", 4),
        ("cvv", 5),
        ("card number", 4),
        ("card details", 4),
        ("verification code", 4),
        ("security code", 4),
        ("scam", 3),
        ("scammer", 3),
        ("scammed", 3),
        ("fraud", 3),
        ("fraudulent", 3),
        ("phishing", 4),
        ("phish", 4),
        ("suspicious", 2),
        ("someone called", 2),
        ("unknown number", 2),
        ("called me", 1),
        ("is that bkash", 3),
        ("claiming to be", 3),
        ("pretending to be", 3),
        ("posing as", 3),
        ("asked for my", 3),
        ("asking for my", 3),
        ("asked my", 3),
        ("asking my", 3),
        ("ask for my", 3),
        ("wants my", 2),
        ("won a prize", 3),
        ("you have won", 3),
        ("lottery", 3),
        ("reward", 2),
        ("gift voucher", 3),
        ("click this link", 3),
        ("click the link", 3),
        ("verify your account", 3),
        ("account will be blocked", 3),
        ("account suspended", 3),
        ("account blocked", 2),
        ("share the code", 3),
        ("send me the code", 3),
        # Bangla
        ("ওটিপি", 5),
        ("পিন", 4),
        ("পাসওয়ার্ড", 4),
        ("কোড চেয়েছে", 4),
        ("প্রতারক", 3),
        ("প্রতারণা", 3),
        ("ফাঁদ", 2),
        ("লটারি", 3),
        ("পুরস্কার", 2),
        ("সন্দেহজনক", 2),
        ("ফোন করে", 2),
        ("কল করে", 2),
    ],
    "wrong_transfer": [
        ("wrong number", 3),
        ("wrong recipient", 3),
        ("wrong account", 3),
        ("wrong person", 3),
        ("wrong mobile", 3),
        ("wrong bkash", 3),
        ("wrong nagad", 3),
        ("to the wrong", 2),
        ("to a wrong", 2),
        ("to wrong", 2),
        ("incorrect number", 3),
        ("incorrect recipient", 3),
        ("incorrect account", 3),
        ("mistakenly", 2),
        ("by mistake", 2),
        ("accidentally", 2),
        ("sent by mistake", 3),
        ("sent it to the wrong", 3),
        ("wrong digit", 2),
        ("typo in the number", 2),
        # Bangla
        ("ভুল নাম্বার", 3),
        ("ভুল নম্বর", 3),
        ("ভুল করে", 2),
        ("ভুলবশত", 2),
        ("ভুল একাউন্ট", 3),
        ("ভুল অ্যাকাউন্ট", 3),
        ("ভুল মানুষ", 3),
    ],
    "payment_failed": [
        ("payment failed", 4),
        ("payment unsuccessful", 4),
        ("transaction failed", 4),
        ("transaction unsuccessful", 4),
        ("failed transaction", 4),
        ("failed payment", 4),
        ("balance deducted", 3),
        ("money deducted", 3),
        ("amount deducted", 3),
        ("balance cut", 3),
        ("money cut", 3),
        ("debited but", 3),
        ("deducted but", 3),
        ("charged but", 3),
        ("double charged", 3),
        ("charged twice", 3),
        ("didn't go through", 2),
        ("did not go through", 2),
        ("not completed", 2),
        ("transaction pending", 2),
        ("payment stuck", 3),
        ("cash out failed", 3),
        ("send money failed", 3),
        ("recharge failed", 3),
        ("bill payment failed", 3),
        # Bangla
        ("পেমেন্ট ফেইল", 4),
        ("লেনদেন ব্যর্থ", 4),
        ("টাকা কেটে", 3),
        ("ব্যালেন্স কেটে", 3),
        ("কেটে নিয়েছে", 3),
        ("টাকা কাটা", 3),
    ],
    "refund_request": [
        ("refund", 3),
        ("money back", 3),
        ("return my money", 3),
        ("return the money", 3),
        ("want my money back", 3),
        ("get my money back", 3),
        ("changed my mind", 2),
        ("cancel my order", 2),
        ("cancel the order", 2),
        ("reverse the transaction", 2),
        ("reimburse", 2),
        # Bangla
        ("রিফান্ড", 3),
        ("টাকা ফেরত", 3),
        ("ফেরত", 2),
    ],
}

# Phrases that confirm a ticket is a genuine "other" (technical / general)
# issue. They do not pick the category, but they raise confidence that "other"
# is a deliberate classification rather than a fallback shrug.
OTHER_HINTS: list[str] = [
    "app crashed",
    "app crash",
    "app not working",
    "app is not working",
    "cannot login",
    "can't log in",
    "cant login",
    "login issue",
    "login problem",
    "app slow",
    "app is slow",
    "update",
    "how do i",
    "how to",
    "question about",
    "not loading",
    "blank screen",
    "অ্যাপ",
    "লগইন",
]

# --------------------------------------------------------------------------- #
# Severity modifiers
# --------------------------------------------------------------------------- #
# Presence of any of these forces severity to at least the named level.
CRITICAL_WORDS: list[str] = [
    "stolen",
    "money stolen",
    "hacked",
    "account hacked",
    "unauthorized",
    "unauthorised",
    "compromised",
    "account compromised",
    "taken over",
    "account takeover",
    "all my money",
    "life savings",
    "without my permission",
    "without my knowledge",
    "didn't authorize",
    "did not authorize",
    "emergency",
    # Bangla
    "চুরি",
    "হ্যাক",
    "অনুমতি ছাড়া",
]

HIGH_WORDS: list[str] = [
    "urgent",
    "urgently",
    "immediately",
    "asap",
    "right now",
    "as soon as possible",
    "salary",
    "rent",
    "help fast",
    # Bangla
    "জরুরি",
    "দ্রুত",
]

# Refund-specific: turns a plain refund into a contested dispute (which routes
# to dispute_resolution and lifts severity off the floor).
CONTESTED_WORDS: list[str] = [
    "not received",
    "never received",
    "didn't receive",
    "did not receive",
    "not delivered",
    "defective",
    "wrong item",
    "double charged",
    "charged twice",
    "complaint",
    "refused",
    "without reason",
    "fake product",
    "not as described",
]

# Used only to enrich the agent summary for payment failures.
DEDUCTION_WORDS: list[str] = [
    "deducted",
    "debited",
    "balance cut",
    "money cut",
    "charged",
    "কেটে",
    "কাটা",
]
