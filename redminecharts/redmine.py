from asyncio import coroutine
import json
from posixpath import join

import aiohttp
from redmine.utilities import is_string, to_string, json_response
from redmine.exceptions import (
    AuthError, ConflictError, ImpersonateError, ServerError, ValidationError,
    ResourceNotFoundError, RequestEntityTooLargeError, UnknownError,
    ForbiddenError, JSONDecodeError)


class AsyncRedmine:
    def __init__(self, url, *, username=None, password=None, key=None,
                 requests={}, impersonate=None):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.key = key
        self.requests = requests
        self.impersonate = impersonate

    @coroutine
    def request(self, method, url, headers=None, params=None, data=None,
                raw_response=False):
        """Make requests to Redmine and returns result in json format."""
        kwargs = dict(self.requests, **{
            'headers': headers or {},
            'params': params or {},
            'data': data or {},
        })

        if ('Content-Type' not in kwargs['headers'] and
                method in ('post', 'put')):
            kwargs['data'] = json.dumps(data)
            kwargs['headers']['Content-Type'] = 'application/json'

        if self.impersonate is not None:
            kwargs['headers']['X-Redmine-Switch-User'] = self.impersonate

        # We would like to be authenticated by API key by default
        if 'key' not in kwargs['params'] and self.key is not None:
            kwargs['params']['key'] = self.key
        else:
            kwargs['auth'] = (self.username, self.password)

        api_url = join(self.url, url + '.json')
        response = yield from aiohttp.request(method, api_url, **kwargs)

        if response.status in (200, 201):
            if raw_response:
                return response
            text = yield from response.text()
            if not text.strip():
                return True
            else:
                try:
                    return json.loads(text)
                except (ValueError, TypeError):
                    raise JSONDecodeError
        elif response.status == 401:
            raise AuthError
        elif response.status == 403:
            raise ForbiddenError
        elif response.status == 404:
            raise ResourceNotFoundError
        elif response.status == 409:
            raise ConflictError
        elif response.status == 412 and self.impersonate is not None:
            raise ImpersonateError
        elif response.status == 413:
            raise RequestEntityTooLargeError
        elif response.status == 422:
            response_json = yield from response.json()
            errors = json_response(response_json)['errors']
            raise ValidationError(to_string(', '.join(e if is_string(e)
                                            else ': '.join(e)
                                            for e in errors)))
        elif response.status == 500:
            raise ServerError

        raise UnknownError(response.status)
