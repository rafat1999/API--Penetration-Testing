'''
This module contains the TestGenerator class which is used to generate API test checks.
'''
from copy import deepcopy
from .fuzzer import fill_params
from .post_test_processor import PostTestFiltersEnum
from .fuzzer import generate_random_int
from ..config_data_handler import populate_user_data
from ..parsers import SwaggerParser, OpenAPIv3Parser
from ..utils import join_uri_path, get_unique_params


class TestGenerator:
    """
    Class to generate API test checks.

    This class provides methods to generate API test checks for various scenarios.

    Attributes:
        None

    Methods:
        check_unsupported_http_methods: Checks whether endpoint supports
        undocumented/unsupported HTTP methods.
        sqli_fuzz_params: Performs SQL injection (SQLi) parameter fuzzing
        based on the provided OpenAPIParser instance.
    """

    def __init__(self, headers: dict = None) -> None:  # type: ignore
        """
        Initializes an instance of the TestGenerator class.

        Args:
            headers (dict, optional): A dictionary of headers to be set
            for the instance. Defaults to None.

        Returns:
            None

        Example:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer xyz123"}
            tester = TestGenerator(headers)
        """
        self._headers = headers

    def check_unsupported_http_methods(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        *args,
        success_codes: list[int] | None = None,
        **kwargs,
    ):
        '''Checks whether endpoint supports undocumented/unsupported HTTP methods

        Args:
            base_url (str): The base URL to check for unsupported HTTP methods.
            endpoints (list[tuple]): A list of tuples representing the endpoints
            to check. Each tuple should contain the endpoint path and the
            corresponding supported HTTP methods.
            success_codes (list[int], optional): A list of HTTP success codes to consider as
            successful responses. Defaults to [ 200, 201, 301, 302 ].
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None

        Raises:
            Any exceptions raised during the execution.
        '''
        if success_codes is None:
            success_codes = [200, 201, 301, 302]

        tasks = []
        fuzzed_endpoints = self.__fuzz_request_params(openapi_parser)
        endpoints_index = {}

        for fuzzed_endpoint_data in fuzzed_endpoints:
            endpoint = fuzzed_endpoint_data['endpoint']
            method = fuzzed_endpoint_data['method']

            if endpoint not in endpoints_index:
                endpoints_index[endpoint] = {
                    'endpoints': [],
                    'methods': [],
                    'body_params': [],
                    'query_params': [],
                    'path_params': [],
                }

            endpoints_index[endpoint]['endpoints'].append(fuzzed_endpoint_data)
            if method not in endpoints_index[endpoint]['methods']:
                endpoints_index[endpoint]['methods'].append(method.lower())

            endpoints_index[endpoint]['body_params'].extend(
                fuzzed_endpoint_data['body_params']
            )
            endpoints_index[endpoint]['query_params'].extend(
                fuzzed_endpoint_data['query_params']
            )
            endpoints_index[endpoint]['path_params'].extend(
                fuzzed_endpoint_data['path_params']
            )

        for endpoint, endpoint_dict in endpoints_index.items():
            methods_allowed = endpoint_dict.get('methods', [])
            body_params = endpoint_dict.get('body_params', [])
            path_params = endpoint_dict.get('path_params', [])
            query_params = endpoint_dict.get('query_params', [])
            url = join_uri_path(openapi_parser.base_url, endpoint)

            http_methods: set = {'get', 'post', 'put', 'patch', 'delete', 'options'}
            restricted_methods = http_methods - set(methods_allowed)

            for restricted_method in restricted_methods:
                tasks.append(
                    {
                        'test_name': 'UnSupported HTTP Method Check',
                        'url': url,
                        'endpoint': endpoint,
                        'method': restricted_method.upper(),
                        'malicious_payload': [],
                        'args': args,
                        'kwargs': kwargs,
                        'vuln_details': {
                            True: 'Endpoint performs HTTP verb which is not documented',
                            False: "Endpoint doesn't perform any HTTP verb which is not documented",
                        },
                        'body_params': body_params,
                        'query_params': query_params,
                        'path_params': path_params,
                        'success_codes': success_codes,
                        'response_filter': PostTestFiltersEnum.STATUS_CODE_FILTER.name,
                    }
                )

        return tasks

    def __fuzz_request_params(
        self, openapi_parser: SwaggerParser | OpenAPIv3Parser
    ) -> list[dict]:
        """
        Fuzzes Request params available in different positions and returns a list
        of tasks

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.

        Returns:
            list: returns list of dict (tasks) for API testing with fuzzed request params
        """
        base_url: str = openapi_parser.base_url
        request_response_params: list[dict] = openapi_parser.request_response_params

        tasks = []
        for path_obj in request_response_params:
            # handle path params from request_params
            request_params = path_obj.get('request_params', [])
            request_params = fill_params(request_params, openapi_parser.is_v3)
            security = path_obj.get('security', [])

            # get params based on their position in request
            request_body_params = list(
                filter(lambda x: x.get('in') == 'body', request_params)
            )
            request_query_params = list(
                filter(lambda x: x.get('in') == 'query', request_params)
            )
            path_params_in_body = list(
                filter(lambda x: x.get('in') == 'path', request_params)
            )

            # get endpoint path
            endpoint_path: str = path_obj.get('path')  # type: ignore

            # get path params and fill them
            path_params = path_obj.get('path_params', [])
            path_params = fill_params(path_params, openapi_parser.is_v3)

            # get unique path params
            path_params = get_unique_params(path_params, path_params_in_body)

            for path_param in path_params:
                path_param_name = path_param.get('name')
                path_param_value = path_param.get('value')

                endpoint_path = endpoint_path.replace(
                    '{' + str(path_param_name) + '}', str(path_param_value)
                )

            tasks.append(
                {
                    'url': join_uri_path(
                        base_url, openapi_parser.api_base_path, endpoint_path
                    ),
                    'endpoint': join_uri_path(
                        openapi_parser.api_base_path, endpoint_path
                    ),
                    'method': path_obj.get('http_method', '').upper(),
                    'body_params': request_body_params,
                    'query_params': request_query_params,
                    'path_params': path_params,
                    'security': security,
                }
            )

        return tasks

    def __inject_payload_in_params(self, request_params: list[dict], payload: str):
        """
        Injects payload into the request parameters.

        This method modifies the provided request parameters by injecting the SQLi payload.

        Args:
            request_params (list[dict]): A list of dictionaries representing the request parameters.
            payload (str): The injection payload to be injected into the request parameters.

        Returns:
            list: returns list of sqli injection parameters for API testing
        """
        request_params = deepcopy(request_params)

        # inject sqli payload as param value
        for request_param_data in request_params:
            # TODO: inject sqli payloads in other data types as well
            if request_param_data.get('type') == 'string':
                request_param_data['value'] = payload

        return request_params

    def sqli_fuzz_params_test(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        *args,
        success_codes: list[int] | None = None,
        **kwargs,
    ):
        '''Performs SQL injection (SQLi) parameter fuzzing based on the
        provided OpenAPIParser instance.

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            success_codes (list[int], optional): A list of HTTP success codes to
            consider as successful SQLi responses. Defaults to [500].
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List: List of dictionaries containing tests for SQLi

        Raises:
            Any exceptions raised during the execution.
        '''
        if success_codes is None:
            success_codes = [500]

        # APPROACH: first send sqli in all params, if error is generated
        # then enumerate one by one or ask user to pentest manually using
        # sqlmap
        tasks = []
        basic_sqli_payloads = [
            "' OR 1=1 ;--",
            "' UNION SELECT 1,2,3 -- -",
            "' OR '1'='1--",
            "' AND (SELECT * FROM (SELECT(SLEEP(5)))abc)",
            "' AND SLEEP(5) --",
        ]

        fuzzed_request_list = self.__fuzz_request_params(openapi_parser)

        # inject SQLi payloads in string variables
        for sqli_payload in basic_sqli_payloads:
            for request_obj in fuzzed_request_list:
                # handle body request params
                body_request_params = request_obj.get('body_params', [])
                malicious_body_request_params = self.__inject_payload_in_params(
                    body_request_params, sqli_payload
                )

                # handle query request params
                query_request_params = request_obj.get('query_params', [])
                malicious_query_request_params = self.__inject_payload_in_params(
                    query_request_params, sqli_payload
                )

                # BUG: for few SQLi test, path params injected value is not matching
                # with final URI path params in output
                request_obj['test_name'] = 'SQLi Test'

                request_obj['body_params'] = malicious_body_request_params
                request_obj['query_params'] = malicious_query_request_params
                request_obj['args'] = args
                request_obj['kwargs'] = kwargs

                request_obj['malicious_payload'] = sqli_payload

                request_obj['vuln_details'] = {
                    True: 'One or more parameter is vulnerable to SQL Injection Attack',
                    False: 'Parameters are not vulnerable to SQLi Payload',
                }
                request_obj['success_codes'] = success_codes
                request_obj[
                    'response_filter'
                ] = PostTestFiltersEnum.STATUS_CODE_FILTER.name
                tasks.append(deepcopy(request_obj))

        return tasks

    def sqli_in_uri_path_fuzz_test(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        *args,
        success_codes: list[int] | None = None,
        **kwargs,
    ):
        '''Generate Tests for SQLi in endpoint path

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            success_codes (list[int], optional): A list of HTTP success codes to
            consider as successful BOLA responses. Defaults to [200, 201, 301].
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list[dict]: list of dict containing test case for endpoint

        Raises:
            Any exceptions raised during the execution.
        '''
        if success_codes is None:
            success_codes = [500]

        base_url: str = openapi_parser.base_url
        request_response_params: list[dict] = openapi_parser.request_response_params

        # filter path containing params in path
        endpoints_with_param_in_path = list(
            filter(
                lambda path_obj: '/{' in path_obj.get('path'),  # type: ignore
                request_response_params,  # type: ignore
            )  # type: ignore
        )

        basic_sqli_payloads = [
            "' OR 1=1 ;--",
            "' UNION SELECT 1,2,3 -- -",
            "' OR '1'='1--",
            "' AND (SELECT * FROM (SELECT(SLEEP(5)))abc)",
            "' AND SLEEP(5) --",
        ]

        tasks = []
        for sqli_payload in basic_sqli_payloads:
            for path_obj in endpoints_with_param_in_path:
                # handle path params from request_params
                request_params = path_obj.get('request_params', [])
                request_params = fill_params(request_params, openapi_parser.is_v3)

                # get request body params
                request_body_params = list(
                    filter(lambda x: x.get('in') == 'body', request_params)
                )

                # handle path params from path_params
                # and replace path params by value in
                # endpoint path
                endpoint_path: str = path_obj.get('path')

                path_params = path_obj.get('path_params', [])
                path_params_in_body = list(
                    filter(lambda x: x.get('in') == 'path', request_params)
                )
                path_params += path_params_in_body
                path_params = fill_params(path_params, openapi_parser.is_v3)

                for path_param in path_params:
                    path_param_name = path_param.get('name')
                    endpoint_path = endpoint_path.replace(
                        '{' + str(path_param_name) + '}', str(sqli_payload)
                    )

                request_query_params = list(
                    filter(lambda x: x.get('in') == 'query', request_params)
                )

                tasks.append(
                    {
                        'test_name': 'SQLi Test in URI Path with Fuzzed Params',
                        'url': join_uri_path(
                            base_url, openapi_parser.api_base_path, endpoint_path
                        ),
                        'endpoint': join_uri_path(
                            openapi_parser.api_base_path, endpoint_path
                        ),
                        'method': path_obj.get('http_method').upper(),
                        'body_params': request_body_params,
                        'query_params': request_query_params,
                        'path_params': path_params,
                        'malicious_payload': sqli_payload,
                        'args': args,
                        'kwargs': kwargs,
                        'vuln_details': {
                            True: 'Endpoint might be vulnerable to SQli',
                            False: 'Endpoint is not vulnerable to SQLi',
                        },
                        'success_codes': success_codes,
                        'response_filter': PostTestFiltersEnum.STATUS_CODE_FILTER.name,
                    }
                )

        return tasks

    def bola_fuzz_path_test(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        *args,
        success_codes: list[int] | None = None,  # type: ignore
        **kwargs,
    ):
        '''Generate Tests for BOLA in endpoint path

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            success_codes (list[int], optional): A list of HTTP success codes to consider
            as successful BOLA responses. Defaults to [200, 201, 301].
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list[dict]: list of dict containing test case for endpoint

        Raises:
            Any exceptions raised during the execution.
        '''
        if success_codes is None:
            success_codes: list[int] = [200, 201, 301]

        base_url: str = openapi_parser.base_url
        request_response_params: list[dict] = openapi_parser.request_response_params

        # filter path containing params in path
        endpoints_with_param_in_path = list(
            filter(
                lambda path_obj: '/{' in path_obj.get('path'), request_response_params  # type: ignore
            )  # type: ignore
        )

        tasks = []
        for path_obj in endpoints_with_param_in_path:
            # handle path params from request_params
            request_params = path_obj.get('request_params', [])
            request_params = fill_params(request_params, openapi_parser.is_v3)

            # get request body params
            request_body_params = list(
                filter(lambda x: x.get('in') == 'body', request_params)
            )

            endpoint_path: str = path_obj.get('path')

            path_params = path_obj.get('path_params', [])
            path_params_in_body = list(
                filter(lambda x: x.get('in') == 'path', request_params)
            )
            path_params = fill_params(path_params, openapi_parser.is_v3)
            path_params = get_unique_params(path_params_in_body, path_params)

            for path_param in path_params:
                path_param_name = path_param.get('name')
                path_param_value = path_param.get('value')
                endpoint_path = endpoint_path.replace(
                    '{' + str(path_param_name) + '}', str(path_param_value)
                )

            request_query_params = list(
                filter(lambda x: x.get('in') == 'query', request_params)
            )

            tasks.append(
                {
                    'test_name': 'BOLA Path Test with Fuzzed Params',
                    'url': join_uri_path(
                        base_url, openapi_parser.api_base_path, endpoint_path
                    ),
                    'endpoint': join_uri_path(
                        openapi_parser.api_base_path, endpoint_path
                    ),
                    'method': path_obj.get('http_method').upper(),
                    'body_params': request_body_params,
                    'query_params': request_query_params,
                    'path_params': path_params,
                    'malicious_payload': path_params,
                    'args': args,
                    'kwargs': kwargs,
                    'vuln_details': {
                        True: 'Endpoint might be vulnerable to BOLA',
                        False: 'Endpoint is not vulnerable to BOLA',
                    },
                    'success_codes': success_codes,
                    'response_filter': PostTestFiltersEnum.STATUS_CODE_FILTER.name,
                }
            )

        return tasks

    def bola_fuzz_trailing_slash_path_test(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        *args,
        success_codes: list[int] | None = None,  # type: ignore
        **kwargs,
    ):
        '''Generate Tests for BOLA in endpoint path

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            success_codes (list[int], optional): A list of HTTP success codes to
            consider as successful BOLA responses. Defaults to [200, 201, 301].
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list[dict]: list of dict containing test case for endpoint

        Raises:
            Any exceptions raised during the execution.
        '''
        if success_codes is None:
            success_codes: list[int] = [200, 201, 301]

        base_url: str = openapi_parser.base_url
        request_response_params: list[dict] = openapi_parser.request_response_params

        tasks = []
        for path_obj in request_response_params:
            # handle path params from request_params
            request_params = path_obj.get('request_params', [])
            request_params = fill_params(request_params, openapi_parser.is_v3)

            # get params based on their position in request
            request_body_params = list(
                filter(lambda x: x.get('in') == 'body', request_params)
            )
            request_query_params = list(
                filter(lambda x: x.get('in') == 'query', request_params)
            )
            path_params_in_body = list(
                filter(lambda x: x.get('in') == 'path', request_params)
            )

            # get endpoint path
            endpoint_path: str = path_obj.get('path')  # type: ignore

            # get path params and fill them
            path_params = path_obj.get('path_params', [])
            path_params = fill_params(path_params, openapi_parser.is_v3)

            # get unique path params
            path_params = get_unique_params(path_params, path_params_in_body)

            for path_param in path_params:
                path_param_name = path_param.get('name')
                path_param_value = path_param.get('value')
                endpoint_path = endpoint_path.replace(
                    '{' + str(path_param_name) + '}', str(path_param_value)
                )

            # generate URL for BOLA attack
            url = join_uri_path(base_url, openapi_parser.api_base_path, endpoint_path)
            malicious_payload = generate_random_int()
            if url.endswith('/'):
                url = f'{url}{malicious_payload}'
            else:
                url = f'{url}/{malicious_payload}'

            tasks.append(
                {
                    'test_name': 'BOLA Path Trailing Slash Test',
                    'url': url,
                    'endpoint': join_uri_path(
                        openapi_parser.api_base_path, endpoint_path
                    ),
                    'method': path_obj.get('http_method').upper(),  # type: ignore
                    'body_params': request_body_params,
                    'query_params': request_query_params,
                    'path_params': path_params,
                    'malicious_payload': malicious_payload,
                    'args': args,
                    'kwargs': kwargs,
                    'vuln_details': {
                        True: 'Endpoint might be vulnerable to BOLA',
                        False: 'Endpoint might not vulnerable to BOLA',
                    },
                    'success_codes': success_codes,
                    'response_filter': PostTestFiltersEnum.STATUS_CODE_FILTER.name,
                }
            )

        return tasks

    def _inject_response_params(self, response_params: dict, is_v3: bool = False):
        '''Populate response params in body params for testing
        BOPLA attacks.

        Args:
            body_params ([dict]) : dict of response from openapi documentation
            {'200':{'properties':{'schema':{'test_param':{'type':'str'}}}}}

        Returns:
            list[dict]: list of dict containing test case for endpoint

        Raises:
            Any exceptions raised during the execution.
        '''
        # create list for data
        params = []

        for status_code, response_data in response_params.items():
            properties = response_data.get('schema', {}).get('properties', {})
            for name, param_data in properties.items():
                param_data['name'] = name
                param_data['in'] = 'body'
                param_data['status_code'] = status_code
                params.append(deepcopy(param_data))

        # fuzz data
        params = fill_params(params, is_v3)
        return params

    def bopla_fuzz_test(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        *args,
        success_codes: list[int] | None = None,  # type: ignore
        **kwargs,
    ):
        '''Generate Tests for BOPLA/Mass Assignment Vulnerability

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            success_codes (list[int], optional): A list of HTTP success codes to
            consider as successful BOLA responses. Defaults to [200, 201, 301].
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list[dict]: list of dict containing test case for endpoint

        Raises:
            Any exceptions raised during the execution.
        '''
        if success_codes is None:
            success_codes: list[int] = [200, 201, 301]

        base_url: str = openapi_parser.base_url
        request_response_params: list[dict] = openapi_parser.request_response_params

        tasks = []
        for path_obj in request_response_params:
            # handle path params from request_params
            request_params = path_obj.get('request_params', [])
            request_params = fill_params(request_params, openapi_parser.is_v3)

            # get params based on their position in request
            request_body_params = list(
                filter(lambda x: x.get('in') == 'body', request_params)
            )
            request_query_params = list(
                filter(lambda x: x.get('in') == 'query', request_params)
            )
            path_params_in_body = list(
                filter(lambda x: x.get('in') == 'path', request_params)
            )

            if len(request_body_params) == 0 and len(request_query_params) == 0:
                continue

            # handle path params from path_params
            # and replace path params by value in
            # endpoint path
            endpoint_path: str = path_obj.get('path')  # type: ignore
            path_params = path_obj.get('path_params', [])
            path_params = fill_params(path_params, openapi_parser.is_v3)
            path_params = get_unique_params(path_params_in_body, path_params)

            for path_param in path_params:
                path_param_name = path_param.get('name')
                path_param_value = path_param.get('value')
                endpoint_path = endpoint_path.replace(
                    '{' + str(path_param_name) + '}', str(path_param_value)
                )

            # assign values to response params below and add them to JSON request body
            response_body_params = self._inject_response_params(
                path_obj.get('response_params', []),
                openapi_parser.is_v3,
            )
            request_body_params += response_body_params

            tasks.append(
                {
                    'test_name': 'BOPLA Test',
                    'url': join_uri_path(
                        base_url, openapi_parser.api_base_path, endpoint_path
                    ),
                    'endpoint': join_uri_path(
                        openapi_parser.api_base_path, endpoint_path
                    ),
                    'method': path_obj.get('http_method', '').upper(),
                    'body_params': request_body_params,
                    'query_params': request_query_params,
                    'path_params': path_params,
                    'malicious_payload': response_body_params,
                    'args': args,
                    'kwargs': kwargs,
                    'vuln_details': {
                        True: 'Endpoint might be vulnerable to BOPLA',
                        False: 'Endpoint might not vulnerable to BOPLA',
                    },
                    'success_codes': success_codes,
                    'response_filter': PostTestFiltersEnum.STATUS_CODE_FILTER.name,
                }
            )

        return tasks

    def test_with_user_data(
        self,
        user_data: dict,
        test_generator_method,
        *args,
        test_for_actor1: bool = True,
        test_for_actor2: bool = False,
        **kwargs,
    ):
        '''Generate Tests with user sepecified data using provided test generator method

        Args:
            user_data (dict): User specified YAML data as dict.
            test_generator_method (class method): test generator class method to be
            used for generating API pentest tests.
            test_for_actor1 (bool): Generate tests for actor1 user data
            test_for_actor2 (bool): Generate tests for actor2 user data
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list[dict]: list of dict containing test case for endpoint

        Raises:
            Any exceptions raised during the execution.
        '''
        # generate tests using test generator method
        tests = test_generator_method(*args, **kwargs)
        new_tests = []

        actor1_data = user_data.get('actors', [])[0].get('actor1', {})
        actor2_data = user_data.get('actors', [])[1].get('actor2', {})

        if test_for_actor1:
            new_tests += populate_user_data(actor1_data, 'actor1', tests)

        if test_for_actor2:
            new_tests += populate_user_data(actor2_data, 'actor2', tests)

        return new_tests

    def __generate_injection_fuzz_params_test(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        test_name: str,
        vuln_details: dict,
        payloads_data: list[dict],
        *args,
        **kwargs,
    ):
        '''Performs injection parameter fuzzing based on the provided OpenAPIParser instance
        and matches injected payload using regex in response.

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class containing
            the parsed OpenAPI specification.
            payloads_data (list[dict]): list of dictionary containing malicious request payload
            and regex for matching injection in response.
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List: List of dictionaries containing tests for SQLi

        Raises:
            Any exceptions raised during the execution.
        '''
        # fuzz params
        fuzzed_request_list = self.__fuzz_request_params(openapi_parser)

        # inject command injection payloads in string variables
        tasks = []
        for payload_dict in payloads_data:
            for request_obj in fuzzed_request_list:
                payload = payload_dict['request_payload']
                body_request_params = request_obj.get('body_params', [])
                query_request_params = request_obj.get('query_params', [])
                # endpoint can be fuzzed if it has query/body params
                if len(body_request_params) == 0 and len(query_request_params) == 0:
                    continue

                # handle body and query request params
                malicious_body_request_params = self.__inject_payload_in_params(
                    body_request_params, payload
                )
                malicious_query_request_params = self.__inject_payload_in_params(
                    query_request_params, payload
                )
                request_obj['test_name'] = test_name

                request_obj['body_params'] = malicious_body_request_params
                request_obj['query_params'] = malicious_query_request_params
                request_obj['args'] = args
                request_obj['kwargs'] = kwargs

                request_obj['malicious_payload'] = payload

                request_obj['vuln_details'] = vuln_details
                request_obj[
                    'response_filter'
                ] = PostTestFiltersEnum.BODY_REGEX_FILTER.name
                request_obj['response_match_regex'] = payload_dict.get(
                    'response_match_regex'
                )

                tasks.append(deepcopy(request_obj))

        return tasks

    def os_command_injection_fuzz_params_test(
        self, openapi_parser: SwaggerParser | OpenAPIv3Parser
    ):
        '''Performs OS Command injection parameter fuzzing based on the provided
        OpenAPIParser instance.

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class containing the
            parsed OpenAPI specification.
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List: List of dictionaries containing tests for OS command injection

        Raises:
            Any exceptions raised during the execution.
        '''
        test_name = 'OS Command Injection Test'

        root_regex = r'root:.*'
        payloads_data = [
            {'request_payload': 'cat /etc/passwd', 'response_match_regex': root_regex},
            {'request_payload': 'cat /etc/shadow', 'response_match_regex': root_regex},
            {'request_payload': 'ls -la', 'response_match_regex': r'total\s\d+'},
        ]

        vuln_details = {
            True: 'One or more parameter is vulnerable to OS Command Injection Attack',
            False: 'Parameters are not vulnerable to OS Command Injection',
        }

        return self.__generate_injection_fuzz_params_test(
            openapi_parser=openapi_parser,
            test_name=test_name,
            vuln_details=vuln_details,
            payloads_data=payloads_data,
        )

    def xss_html_injection_fuzz_params_test(
        self, openapi_parser: SwaggerParser | OpenAPIv3Parser
    ):
        '''Performs OS Command injection parameter fuzzing based on the
        provided OpenAPIParser instance.

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List: List of dictionaries containing tests for XSS

        Raises:
            Any exceptions raised during the execution.
        '''
        test_name = 'XSS/HTML Injection Test'

        payloads_data = [
            {
                'request_payload': '<script>confirm(1)</script>',
                'response_match_regex': r'<script[^>]*>.*<\/script>',
            },
            {
                'request_payload': '<script>alert(1)</script>',
                'response_match_regex': r'<script[^>]*>.*<\/script>',
            },
            {
                'request_payload': "<img src=x onerror='javascript:confirm(1),>",
                'response_match_regex': r'<img[^>]*>',
            },
        ]

        vuln_details = {
            False: 'Parameters are not vulnerable to XSS/HTML Injection Attack',
            True: 'One or more parameter is vulnerable to XSS/HTML Injection Attack',
        }

        return self.__generate_injection_fuzz_params_test(
            openapi_parser=openapi_parser,
            test_name=test_name,
            vuln_details=vuln_details,
            payloads_data=payloads_data,
        )

    def ssti_fuzz_params_test(self, openapi_parser: SwaggerParser | OpenAPIv3Parser):
        '''Performs SSTI fuzzing based on the provided OpenAPIParser instance.

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List: List of dictionaries containing tests for SSTI

        Raises:
            Any exceptions raised during the execution.
        '''
        test_name = 'SSTI Test'

        payloads_data = [
            {'request_payload': r'${7777+99999}', 'response_match_regex': r'107776'},
            {'request_payload': r"{{7*'7'}}", 'response_match_regex': r'49'},
            {'request_payload': r"{{7*'7'}}", 'response_match_regex': r'7777777'},
            {
                'request_payload': r"{{ '<script>confirm(1337)</script>' }}",
                'response_match_regex': r'<script>confirm(1337)</script>',
            },
            {
                'request_payload': r"{{ '<script>confirm(1337)</script>' | safe }}",
                'response_match_regex': r'<script>confirm(1337)</script>',
            },
            {
                'request_payload': r"{{'owasp offat'.toUpperCase()}}",
                'response_match_regex': r'OWASP OFFAT',
            },
            {
                'request_payload': r"{{'owasp offat' | upper }}",
                'response_match_regex': r'OWASP OFFAT',
            },
            {
                'request_payload': r"<%= system('cat /etc/passwd') %>",
                'response_match_regex': r'root:.*',
            },
            {'request_payload': r'*{7*7}', 'response_match_regex': r'49'},
        ]

        vuln_details = {
            True: 'One or more parameter is vulnerable to SSTI Attack',
            False: 'Parameters are not vulnerable to SSTI Attack',
        }

        return self.__generate_injection_fuzz_params_test(
            openapi_parser=openapi_parser,
            test_name=test_name,
            vuln_details=vuln_details,
            payloads_data=payloads_data,
        )

    def missing_auth_fuzz_test(
        self,
        openapi_parser: SwaggerParser | OpenAPIv3Parser,
        *args,
        success_codes: list[int] | None = None,  # type: ignore
        **kwargs,
    ):
        '''Generate Tests for API endpoints which documents security authentication but doesn't check for authentication properly

        Args:
            openapi_parser (OpenAPIParser): An instance of the OpenAPIParser class
            containing the parsed OpenAPI specification.
            success_codes (list[int], optional): A list of HTTP success codes to consider
            as test failed responses. Defaults to [200, 201, 301].
            *args: Variable-length positional arguments.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list[dict]: list of dict containing test case for endpoint

        Raises:
            Any exceptions raised during the execution.
        '''
        if success_codes is None:
            success_codes: list[int] = [200, 201, 301]

        base_url: str = openapi_parser.base_url
        request_response_params: list[dict] = openapi_parser.request_response_params

        # pop authorization header from kwargs.headers dict
        kwargs.get('headers', {}).pop('Authorization', None)
        kwargs.get('headers', {}).pop('X-Api-Key', None)

        # filter endpoints which has security definition in their documentation
        endpoints_with_security = list(
            filter(
                lambda path_obj: path_obj.get('security')
                and path_obj.get('security') != [{}],
                request_response_params,  # type: ignore
            )  # type: ignore
        )

        tasks = []
        for path_obj in endpoints_with_security:
            # handle path params from request_params
            request_params = path_obj.get('request_params', [])
            request_params = fill_params(request_params, openapi_parser.is_v3)

            # get request body params
            request_body_params = list(
                filter(lambda x: x.get('in') == 'body', request_params)
            )

            endpoint_path: str = path_obj.get('path')  # type: ignore

            path_params = path_obj.get('path_params', [])
            path_params_in_body = list(
                filter(lambda x: x.get('in') == 'path', request_params)
            )
            path_params = fill_params(path_params, openapi_parser.is_v3)
            path_params = get_unique_params(path_params_in_body, path_params)

            for path_param in path_params:
                path_param_name = path_param.get('name')
                path_param_value = path_param.get('value')
                endpoint_path = endpoint_path.replace(
                    '{' + str(path_param_name) + '}', str(path_param_value)
                )

            request_query_params = list(
                filter(lambda x: x.get('in') == 'query', request_params)
            )

            tasks.append(
                {
                    'test_name': 'Missing Authentication Test with Fuzzed Params',
                    'url': join_uri_path(
                        base_url, openapi_parser.api_base_path, endpoint_path
                    ),
                    'endpoint': join_uri_path(
                        openapi_parser.api_base_path, endpoint_path
                    ),
                    'method': path_obj.get('http_method').upper(),  # type: ignore
                    'body_params': request_body_params,
                    'query_params': request_query_params,
                    'path_params': path_params,
                    'malicious_payload': 'Security Payload Missing',
                    'args': args,
                    'kwargs': kwargs,
                    'vuln_details': {
                        True: 'Endpoint fails to implement security authentication as defined',
                        False: 'Endpoint implements security authentication as defined',
                    },
                    'success_codes': success_codes,
                    'response_filter': PostTestFiltersEnum.STATUS_CODE_FILTER.name,
                }
            )

        return tasks
