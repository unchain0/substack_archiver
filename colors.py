from termcolor import colored
from pyfiglet import figlet_format
import six


def log(string: str, color: str, font="slant", figlet=False) -> None:
    if colored is None:
        six.print_(string, flush=True)
        return

    if not figlet:
        six.print_(colored(string, color), flush=True)
        return

    six.print_(colored(figlet_format(string, font=font), color), flush=True)


def welcome_message() -> None:
    log("Substack Archiver", "green", "slant", True)
    log("Created by: @VitaminCPU", "green")
    log("Version: 2.0", "green")
    log("Github: github.com/pwrtux", "green")
    print("")
    log("========================================", "white")
    log("Welcome to the Substack Archiver", "white")
    log("========================================", "white")
    print("")
