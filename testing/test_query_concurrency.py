import threading
import requests

errors = []


def hit():

    try:

        response = requests.post(
            "http://127.0.0.1:8000/query",
            json={
                "question": "Show all customers"
            },
            timeout=60
        )

        print(
            response.status_code
        )

    except Exception as e:

        errors.append(
            str(e)
        )


def test_concurrent_requests():

    threads = []

    for _ in range(5):

        t = threading.Thread(
            target=hit
        )

        threads.append(t)

        t.start()

    for t in threads:

        t.join(
            timeout=90
        )

    assert len(errors) == 0