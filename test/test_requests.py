import requests
print(f"requests module: {requests}")
print(f"requests module file: {getattr(requests, '__file__', 'No __file__ attribute')}")
print(f"requests attributes: {dir(requests)}")

try:
    response = requests.head('https://www.google.com')
    print(f"Response status code: {response.status_code}")
except Exception as e:
    print(f"Error making HEAD request: {e}")