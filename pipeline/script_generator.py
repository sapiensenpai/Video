"""
script_generator.py
Returns the hardcoded MyMeds UK ad script. No API call needed.
"""

MYMEDS_AD_SCRIPT = {
    "title": "MyMeds_UK_Ad",
    "aspect_ratio": "9:16",
    "output_resolution": [1080, 1920],
    "total_target_duration": 55,
    "voice_id": "N2lVS1w4EtoT3dr4eOWO",
    "voice_settings": {
        "stability": 0.65,
        "similarity_boost": 0.80,
        "style": 0.25,
    },
    "scenes": [
        {
            "scene_number": 1,
            "scene_name": "HOOK",
            "duration_seconds": 5,
            "narration": (
                "You just got prescribed new medication. "
                "You Google it. And now you think you're dying."
            ),
            "screenshot": None,
            "text_overlay": {
                "line1": "You Google your meds...",
                "line2": "Now you think you're dying.",
                "position": "center",
                "style": "bold_white_on_dark",
            },
            "background": "dark_gradient_purple",
            "motion": "slow_zoom_in",
            "notes": (
                "No screenshot. Pure text on dark purple/black gradient. "
                "This is the emotional hook."
            ),
        },
        {
            "scene_number": 2,
            "scene_name": "THE_PROBLEM",
            "duration_seconds": 6,
            "narration": (
                "Every health search gives you American results, dodgy forums, "
                "and AI that hallucinates. None of it applies to your UK prescription."
            ),
            "screenshot": "18_social_ad.jpeg",
            "text_overlay": {
                "line1": "Wrong country. Wrong info.",
                "line2": "Wrong answers.",
                "position": "bottom",
                "style": "bold_white_outline",
            },
            "background": None,
            "motion": "slow_zoom_out",
            "notes": "Show the 'Chat GPT for Health / Bye bye Dr. Google' social post.",
        },
        {
            "scene_number": 3,
            "scene_name": "INTRODUCE_SOLUTION",
            "duration_seconds": 5,
            "narration": (
                "That's why we built My Meds UK. "
                "Real medication data. Straight from the UK regulator."
            ),
            "screenshot": "19_logo.jpeg",
            "text_overlay": {
                "line1": "MyMeds UK",
                "line2": "Powered by MHRA data",
                "position": "below_center",
                "style": "brand_purple",
            },
            "background": "light_gradient_purple",
            "motion": "gentle_pulse_zoom",
            "notes": "Show the MyMeds logo centred on a light purple gradient.",
        },
        {
            "scene_number": 4,
            "scene_name": "FEATURE_SEARCH",
            "duration_seconds": 5,
            "narration": (
                "Search every medicine licensed in the UK. "
                "Patient leaflets, clinical summaries, all official documents, "
                "right in the app."
            ),
            "screenshot": "02_medications_list.jpeg",
            "text_overlay": {
                "line1": "Every UK Medicine",
                "line2": "Official MHRA Documents",
                "position": "top",
                "style": "bold_white_outline",
            },
            "background": None,
            "motion": "pan_up_slow",
            "notes": "Show the All Medications List screenshot.",
        },
        {
            "scene_number": 5,
            "scene_name": "FEATURE_AI_CHAT",
            "duration_seconds": 7,
            "narration": (
                "Got a question? Ask Roger, your AI medication guide. "
                "He uses real UK data to give you answers you can actually trust."
            ),
            "screenshot": "03_chat_roger.jpeg",
            "text_overlay": {
                "line1": "Ask Roger",
                "line2": "AI powered by real UK data",
                "position": "top",
                "style": "bold_white_outline",
            },
            "background": None,
            "motion": "slow_zoom_in",
            "notes": "Show the Chat with Roger screenshot (Mounjaro/Ozempic conversation).",
        },
        {
            "scene_number": 6,
            "scene_name": "FEATURE_INTERACTIONS",
            "duration_seconds": 5,
            "narration": (
                "Taking multiple medicines? "
                "Check for dangerous interactions in seconds. "
                "Warfarin and Tramadol? We'll flag it."
            ),
            "screenshot": "04_drug_interaction.jpeg",
            "text_overlay": {
                "line1": "Drug Interaction Checker",
                "line2": "Know before you mix",
                "position": "top",
                "style": "bold_white_outline",
            },
            "background": None,
            "motion": "slow_zoom_in",
            "notes": "Show the Analyse Drugs screenshot (Warfarin + Tramadol).",
        },
        {
            "scene_number": 7,
            "scene_name": "FEATURE_REMINDERS",
            "duration_seconds": 5,
            "narration": (
                "Set medication reminders so you never miss a dose. "
                "Track your compliance history to stay on top of your health."
            ),
            "screenshot": "05_medication_calendar.jpeg",
            "text_overlay": {
                "line1": "Never Miss a Dose",
                "line2": "Smart Reminders & Tracking",
                "position": "top",
                "style": "bold_white_outline",
            },
            "background": None,
            "motion": "pan_down_slow",
            "notes": "Show the Medication Calendar screenshot with Gabapentine.",
        },
        {
            "scene_number": 8,
            "scene_name": "FEATURE_NHS",
            "duration_seconds": 5,
            "narration": (
                "Even scan your NHS prescription barcode "
                "to instantly import your medicines. "
                "It connects to the real NHS."
            ),
            "screenshot": "17_nhs_prescription.jpeg",
            "text_overlay": {
                "line1": "NHS Connected",
                "line2": "Scan your prescription",
                "position": "top",
                "style": "bold_white_outline",
            },
            "background": None,
            "motion": "slow_zoom_in",
            "notes": "Show the NHS Prescription barcode screen.",
        },
        {
            "scene_number": 9,
            "scene_name": "TRUST_PRIVACY",
            "duration_seconds": 5,
            "narration": (
                "Your data stays yours. Encrypted, GDPR compliant, "
                "and secured with Sign in with Apple. "
                "No ads. No selling your data. Ever."
            ),
            "screenshot": "07_document_privacy.jpeg",
            "text_overlay": {
                "line1": "Secure \u2022 Private \u2022 GDPR",
                "line2": "",
                "position": "bottom",
                "style": "bold_white_outline",
            },
            "background": None,
            "motion": "slow_zoom_out",
            "notes": "Show the privacy/document screenshot.",
        },
        {
            "scene_number": 10,
            "scene_name": "CTA_CLOSE",
            "duration_seconds": 7,
            "narration": (
                "My Meds UK. Your pharmacist in your pocket. "
                "Download free on the App Store today."
            ),
            "screenshot": "01_hero_composite.png",
            "text_overlay": {
                "line1": "Your Pharmacist in Your Pocket",
                "line2": "Download Free on App Store",
                "position": "bottom",
                "style": "brand_purple_bold",
            },
            "background": None,
            "motion": "gentle_pulse_zoom",
            "notes": "Show the hero composite image (3-panel shot).",
        },
    ],
}


def get_script() -> dict:
    """Return the hardcoded MyMeds UK ad script."""
    return MYMEDS_AD_SCRIPT
