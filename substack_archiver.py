
from time import sleep
import requests
import json
import re
import os
from dotenv import load_dotenv
import sys
import colors

load_dotenv("config.env")

USERNAME = os.environ.get('SUBSTACK_USERNAME')
PASSWORD = os.environ.get('SUBSTACK_PASSWORD')


def command_line_parser():
    if len(sys.argv) != 3:
        colors.log("""Usage: python3 substack_archiver.py "SUBSSTACKNAME" "URL", """, "white")
        colors.log("""Example: python3 substack_archiver.py "abc" "https://abc.substack.com" or with custom domain: "name123" "https://abc.com" """, "white")
        print("")
        colors.log("""Notice there is no "/" at the end of the URL input""", "yellow")
        print("")
        sys.exit(1)
    else:
        return sys.argv[1], sys.argv[2]



class SubstackAPIHandler:

    def __init__(self, username, password, substack_handle, base_url, cookies=None, post_requests=None):


        self.username = username
        self.password = password
        self.substack_handle = substack_handle
        self.base_url = base_url
        self.login_url = f"{self.base_url}/api/v1/login" 
        self.post_url = f"{self.base_url}/api/v1/posts?limit=50&offset="
        self.cookies = cookies
        self.post_requests = post_requests
        self.html_path = f"html_dumps/{substack_handle}"
        self.json_path = f"json_dumps/{substack_handle}"  

        
        try:
            os.mkdir(f"html_dumps/{substack_handle}")
            os.mkdir(f"json_dumps/{substack_handle}")
        except FileExistsError:
            colors.log("Folder already exists", "red")
            raise FileExistsError("Folder already exists.")
        


    def login(self):

        if self.username == "" or self.password == "":
            raise ValueError("Please set the SUBSTACK_USERNAME and SUBSTACK_PASSWORD environment variables")
        
        payload = {
            "email": self.username,
            "password": self.password
        }

        response = requests.post(url=self.login_url, data=payload)

        if response.status_code != 200:
            colors.log("Login failed", "red")
            raise ValueError("Login failed. Please check your credentials or the Substack URL.")
        if response.status_code == 200:
            colors.log("Login successful", "green")
            print("")
            colors.log("Fetching posts...", "white")
            print("")


        self.cookies = response.cookies
     

    def get_posts(self):
        post_requests = []
        # iterate. max. 50 posts per page. increase offset +50 in each iteration
        for i in range(0, 500, 50):
            post_url = f"{self.post_url}{i}"
            get_posts = requests.request("GET", post_url, cookies=self.cookies).json()
            if get_posts == []:
                break
            post_requests.append(get_posts)
            sleep(2) # sleep 2 seconds to not get rate limited
        self.post_requests = post_requests


    def dump_to_json(self):
        for i in range(len(self.post_requests)):
            with open(f"{self.json_path}/dump{i}.json", "w") as f:
                json.dump(self.post_requests[i], f)
        return

    def serialize(value): 
        value = str(value)
        value = re.sub(r"[^\w\s-]", "", value)
        return re.sub(r"[-\s]+", "-", value).replace("-", " ")


    def parse_to_html(self):
        all_titles = []
        all_bodies = []
        all_descriptions = []
        body_none = []

        # Parse to multiple HTML files
        for post_request in self.post_requests:
            for post in post_request:
                all_titles.append(post["title"])
                all_descriptions.append(post["description"])
                if post["body_html"] is None:
                    body_none.append(post["title"])
                else:   
                    all_bodies.append(post["body_html"])
                

        for title, body, desciption in zip(all_titles, all_bodies, all_descriptions):
            if body is None:
                continue
            html_template = f"""<!DOCTYPE html> <html lang="en"> <head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>{title}</title> </head> <body> <h1>{title}</h1> <p> {desciption} </p> <p>{body}</p> </body> </html>"""
            file_name = SubstackAPIHandler.serialize(title) 
            with open(f"{self.html_path}/{file_name}.html", "wb") as f:
                f.write(html_template.encode("utf-8"))

        return body_none, all_titles
        




if __name__ == "__main__":

    if USERNAME == "" or PASSWORD == "":
        print("Please set the SUBSTACK_USERNAME and SUBSTACK_PASSWORD environment variables")
        sys.exit(1)

    
    colors.welcome_message()

    substack_handle = command_line_parser()
    api_handler = SubstackAPIHandler(USERNAME, PASSWORD, substack_handle[0], substack_handle[1])
    


    api_handler.login()
    api_handler.get_posts()
    api_handler.dump_to_json()
    html = api_handler.parse_to_html()

    colors.log(f"Number of downloaded posts: {len(html[1])}", "green")
    print("")

    if len(html[0]) != 0:
        colors.log(f"Number of Inaccessible Posts: {len(html[0])}", "red")
        colors.log(f"Probably not a paid subscriber. Are you using a paid subscription account?", "red")
        
    colors.log("Done!", "green", "bold")
    print("")