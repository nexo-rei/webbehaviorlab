"""WebBehaviorLab - an educational web automation & behavior testing lab.

WebBehaviorLab is a beginner-friendly, terminal-based laboratory for
understanding HTTP requests, browser automation, page-load timing, browser
events and basic web performance testing.

SAFETY SCOPE: this tool is designed for localhost, local test servers,
staging environments and websites the user owns or has explicit written
authorization to test. It is NOT a traffic-generation or bot-evasion tool.
"""

__all__ = ["__version__", "APP_NAME"]

from webbehavior.version import __version__

APP_NAME = "WebBehaviorLab"
