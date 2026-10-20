import urllib.request

def fetch(url):
    return urllib.request.urlopen(url, timeout=3).read().decode()

def main():
    raw = fetch("https://example.internal/leaderboard.json")
    print("baseline =", raw[:40])

main()
