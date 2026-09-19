import random
import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def run_with_retry(
    operation: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> T:
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except Exception as error:
            last_error = error

            if attempt >= max_attempts:
                break

            delay = (
                base_delay * (2 ** (attempt - 1))
                + random.uniform(0, 0.5)
            )

            print(
                f"Attempt {attempt} failed. "
                f"Retrying in {delay:.2f} seconds..."
            )

            time.sleep(delay)

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "Retry operation failed without an exception"
    )