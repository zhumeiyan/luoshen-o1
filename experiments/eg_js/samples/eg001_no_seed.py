import random

def sample_rows(rows, k):
    return random.sample(rows, k)

print(sample_rows(list(range(100)), 5))
