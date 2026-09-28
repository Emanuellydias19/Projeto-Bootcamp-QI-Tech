from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


class ConcurrentRequests:
    @staticmethod
    def send_at_the_same_time(request_function, arguments: tuple, times: int) -> list:
        barrier = Barrier(times)

        with ThreadPoolExecutor(max_workers=times) as executor:
            futures = []
            for _request in range(times):
                futures.append(
                    executor.submit(ConcurrentRequests._send_after_barrier, barrier, request_function, arguments)
                )

        results = []
        for future in futures:
            results.append(future.result())

        return results

    @staticmethod
    def _send_after_barrier(barrier: Barrier, request_function, arguments: tuple) -> tuple:
        barrier.wait()
        return request_function(*arguments)
