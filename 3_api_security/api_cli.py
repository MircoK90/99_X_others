

import argparse
import requests


# anlegen user und Token out!
parser = argparse.ArgumentParser()
parser.add_argument("--user_add", action="store_true")
args = parser.parse_args()
if args.user_add:
    response = requests.post(
        url='http://localhost:8000/user/signup',
        json={'username':'mirco', 'password':'pass'}
    )
    print(response.json())
    print("test")
    exit(0)


# hello world out
response = requests.get(
    url='http://localhost:8000/secured',
    headers={
        "Authorization": "Bearer " 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoibWlyY28iLCJleHBpcmVzIjoxNzc5MjcxNjkxLjE0MzAzOX0.f5TTMiOQknDMGdjwDaSTXf4DjIPWQ2BkyMJpLmqT_nc'
    }
)
print(response.json())


# response = requests.post(
#     url='http://localhost:8000/user/login',
#     json={'username':'mirco', 'password':'pass'}
# )
# print(response.json())
