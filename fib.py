import time

def fib(n):
    if n < 0:
        return -1
    elif n == 0:
        return 0
    elif n == 1 or n == 2:
        return 1
    else:
        return fib(n-1) + fib(n-2)

if __name__ == "__main__":
    i = 0
    while True:
        print(f"fib({i}) = {fib(i)}")
        i += 1
        time.sleep(5)
