
from time import sleep
import requests
import json
import re
import os
from dotenv import load_dotenv

load_dotenv("config.env")

USERNAME = os.environ.get('SUBSTACK_USERNAME')
PASSWORD = os.environ.get('SUBSTACK_PASSWORD')


class SubstackAPIHandler:

    def __init__(self, username, password, cookies=None, post_requests=None):
        self.username = username
        self.password = password
        self.login_url = "https://public.substack.com/api/v1/login"
        self.cookies = cookies
        self.post_requests = post_requests

    def login(self):

        if self.username == "" or self.password == "":
            raise ValueError("Please set the SUBSTACK_USERNAME and SUBSTACK_PASSWORD environment variables")
        
        payload = {
            "email": self.username,
            "password": self.password
        }

        response = requests.post(url=self.login_url, data=payload)

        if response.status_code != 200:
            raise ValueError("Login failed. Please check your credentials")
        if response.status_code == 200:
            print("Login successful")

        self.cookies = response.cookies
     

    

    def get_posts(self):
        post_requests = []
        # iterate. max. 50 posts per page. increase offset +50 in each iteration
        for i in range(0, 500, 50):
            post_url = f"https://public.substack.com/api/v1/posts/?limit=50&offset={i}"
            get_posts = requests.request("GET", post_url, cookies=self.cookies).json()
            if get_posts == []:
                break
            post_requests.append(get_posts)
            sleep(2) # sleep 2 seconds to not get rate limited
        self.post_requests = post_requests


    def dump_to_json(self):
        for i in range(len(self.post_requests)):
            with open(f"./json_dumps/dump{i}.json", "w") as f:
                json.dump(self.post_requests[i], f)
        return

    def serialize(value):
        value = re.sub(r"[^\w\s-]", "", value.lower())
        return re.sub(r"[-\s]+", "-", value).strip("-_")


    def parse_to_html(self):
        all_titles = []
        all_bodies = []
        all_descriptions = []

        # Parse to multiple HTML files
        for post_request in self.post_requests:
            for post in post_request:
                all_titles.append(post["title"])
                all_bodies.append(post["body_html"])
                all_descriptions.append(post["description"])

        for title, body, desciption in zip(all_titles, all_bodies, all_descriptions):
            html_template = f"""<!DOCTYPE html> <html lang="en"> <head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>{title}</title> </head> <body> <h1>{title}</h1> <p> {desciption} </p> <p>{body}</p> </body> </html>"""
            file_name = SubstackAPIHandler.serialize(title) 
            with open(f"./html_dumps/{file_name}.html", "wb") as f:
                f.write(html_template.encode("utf-8"))
        




if __name__ == "__main__":
    api_handler = SubstackAPIHandler(USERNAME, PASSWORD)
    api_handler.login()
    api_handler.get_posts()
    api_handler.dump_to_json()
    api_handler.parse_to_html()
        
