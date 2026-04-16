def parse_device_name(user_agent: str) -> str:
    """Parse a user-agent string into a human-readable device name."""
    if not user_agent:
        return "Unknown device"

    try:
        from user_agents import parse
        ua = parse(user_agent)
        browser = ua.browser.family or "Unknown browser"
        os_name = ua.os.family or "Unknown OS"
        return f"{browser} on {os_name}"
    except ImportError:
        # Fallback without user-agents library
        if "Chrome" in user_agent:
            browser = "Chrome"
        elif "Firefox" in user_agent:
            browser = "Firefox"
        elif "Safari" in user_agent:
            browser = "Safari"
        elif "Edge" in user_agent:
            browser = "Edge"
        else:
            browser = "Unknown"

        if "Windows" in user_agent:
            os_name = "Windows"
        elif "Mac" in user_agent:
            os_name = "macOS"
        elif "Linux" in user_agent:
            os_name = "Linux"
        elif "Android" in user_agent:
            os_name = "Android"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            os_name = "iOS"
        else:
            os_name = "Unknown OS"

        return f"{browser} on {os_name}"
