import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Union, Callable
import time


class TestClient:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.session = requests.Session()
        if token:
            self.set_token(token)

    def set_token(self, token: str):
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        return self.session.request(method, url, **kwargs)

    def get(self, endpoint: str, params: Dict = None) -> requests.Response:
        return self._make_request("GET", endpoint, params=params)

    def post(
        self, endpoint: str, data: Dict = None, json: Dict = None
    ) -> requests.Response:
        return self._make_request("POST", endpoint, data=data, json=json)

    def _run_concurrent_requests(
        self, request_func: Callable, args_list: List[Dict], max_workers: int = 10
    ) -> List[requests.Response]:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(request_func, **args) for args in args_list]
            return [future.result() for future in as_completed(futures)]

    def concurrent_get(
        self,
        endpoints: List[str],
        params_list: List[Dict] = None,
        max_workers: int = 10,
    ) -> List[requests.Response]:
        if params_list is None:
            params_list = [{}] * len(endpoints)
        args_list = [
            {"endpoint": endpoint, "params": params}
            for endpoint, params in zip(endpoints, params_list)
        ]
        return self._run_concurrent_requests(self.get, args_list, max_workers)

    def concurrent_post(
        self,
        endpoints: List[str],
        data_list: List[Dict] = None,
        json_list: List[Dict] = None,
        max_workers: int = 10,
    ) -> List[requests.Response]:
        args_list = []
        for i, endpoint in enumerate(endpoints):
            args = {"endpoint": endpoint}
            if data_list:
                args["data"] = data_list[i]
            if json_list:
                args["json"] = json_list[i]
            args_list.append(args)
        return self._run_concurrent_requests(self.post, args_list, max_workers)

    def run_load_test(
        self,
        method: str,
        endpoint: str,
        num_requests: int,
        max_workers: int = 10,
        **kwargs,
    ) -> Dict:
        start_time = time.time()

        if method.upper() == "GET":
            responses = self.concurrent_get(
                [endpoint] * num_requests,
                [kwargs.get("params", {})] * num_requests,
                max_workers,
            )
        elif method.upper() == "POST":
            responses = self.concurrent_post(
                [endpoint] * num_requests,
                [kwargs.get("data")] * num_requests,
                [kwargs.get("json")] * num_requests,
                max_workers,
            )
        else:
            raise ValueError("Unsupported HTTP method")

        end_time = time.time()
        total_time = end_time - start_time

        status_codes = [r.status_code for r in responses]

        return {
            "total_requests": num_requests,
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "average_response_time": total_time / num_requests,
            "status_code_counts": {
                code: status_codes.count(code) for code in set(status_codes)
            },
        }
