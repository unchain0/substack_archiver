from termcolor import colored
from pyfiglet import figlet_format
import six

def log(string, color, font="slant", figlet=False):
    if colored:
        if not figlet:
            six.print_(colored(string, color))
        else:
            six.print_(colored(figlet_format(
                string, font=font), color))
    else:
        six.print_(string)


def welcome_message():
    log("Substack Archiver", "green", "slant", True)
    log("Created by: @VitaminCPU", "green")
    log("Version: 2.0", "green")
    log("Github: github.com/pwrtux", "green")
    print("")
    log("========================================", "white")
    log("Welcome to the Substack Archiver", "white")
    log("========================================", "white")
    print("")
    