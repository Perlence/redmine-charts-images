from asyncio import coroutine, wait, gather
from collections import defaultdict
from io import BytesIO
from os.path import dirname

from aiohttp import web
from flask import Config
import arrow
import pygal

from .redmine import AsyncRedmine


config = Config(dirname(__file__))
config.from_pyfile('default.cfg')
config.from_pyfile('settings.cfg')

pygal_config = pygal.Config(style=config['PYGAL_STYLE'])

redmine = AsyncRedmine(config['REDMINE_URL'], key=config['API_KEY'])
issue_statuses = []


@coroutine
def redminecharts(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/issues_by_status', issues_by_status)
    app.router.add_route('GET', '/issues_per_frame', issues_per_frame)
    app.router.add_route('GET', '/today_issues', today_issues)

    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 5000)
    print('Server started at http://127.0.0.1:5000')

    resp = yield from redmine.request('get', 'issue_statuses')
    global issue_statuses
    issue_statuses = resp['issue_statuses']

    return srv


@coroutine
def issues_by_status(request):
    project_id = int(request.GET.get('project_id'))

    issues_by_status = defaultdict(int)

    @coroutine
    def get_issues(status):
        resp = yield from redmine.request(
            'get', 'issues',
            params={
                'project_id': project_id,
                'status_id': status['id'],
                'limit': 1
            })
        issues_by_status[status['name']] = resp['total_count']

    yield from wait(map(get_issues, issue_statuses))

    chart = pygal.Pie(pygal_config)
    for key, value in sort_by_value(issues_by_status, reverse=True):
        chart.add(key, value)
    return render_png_response(chart)


@coroutine
def issues_per_frame(request):
    now = arrow.get()
    project_id = int(request.GET.get('project_id'))
    start = request.GET.get('start', now.floor('year'))
    end = request.GET.get('end', now)
    frame = request.GET.get('frame', 'month')

    if not isinstance(start, arrow.Arrow):
        start = arrow.get(start)
    if not isinstance(end, arrow.Arrow):
        end = arrow.get(end)

    issues_per_frame = defaultdict(int)

    @coroutine
    def get_issues(s):
        e = min(s.ceil(frame), end)
        fmt = 'YYYY-MM-DD'
        query = '><{}|{}'.format(s.format(fmt), e.format(fmt))
        created_coro = redmine.request(
            'get', 'issues',
            params={
                'project_id': project_id,
                'status_id': '*',
                'created_on': query,
                'limit': 1,
            })
        closed_coro = redmine.request(
            'get', 'issues',
            params={
                'project_id': project_id,
                'status_id': 'closed',
                'closed_on': query,
                'limit': 1,
            })
        created, closed = yield from gather(created_coro, closed_coro)
        issues_per_frame[s] = {
            'Created': created['total_count'],
            'Closed': closed['total_count'],
        }

    date_range = arrow.Arrow.range(frame, start, end)
    yield from wait(map(get_issues, date_range))

    chart = pygal.Bar(pygal_config)
    chart.x_labels = [format(d, 'MMM/YY') for d in date_range]
    for name in ('Created', 'Closed'):
        chart.add(name, [issues_per_frame[d][name] for d in date_range])
    return render_png_response(chart)


@coroutine
def today_issues(request):
    project_id = int(request.GET.get('project_id'))

    today = arrow.get().format('YYYY-MM-DD')
    created_coro = redmine.request(
        'get', 'issues',
        params={
            'project_id': project_id,
            'status_id': '*',
            'created_on': today,
            'limit': 1,
        })
    closed_coro = redmine.request(
        'get', 'issues',
        params={
            'project_id': project_id,
            'status_id': 'closed',
            'closed_on': today,
            'limit': 1,
        })
    created, closed = yield from gather(created_coro, closed_coro)

    chart = pygal.Bar(pygal_config)
    chart.add('Created', created['total_count'])
    chart.add('Closed', closed['total_count'])
    return render_png_response(chart)


def sort_by_key(mapping, **kwargs):
    return sorted(mapping.items(), key=lambda item: item[0], **kwargs)


def sort_by_value(mapping, **kwargs):
    return sorted(mapping.items(), key=lambda item: item[1], **kwargs)


def render_response(chart, **kwargs):
    return web.Response(body=chart.render(**kwargs),
                        content_type='image/svg+xml')


def render_png_response(chart, dpi=72, **kwargs):
    file_obj = BytesIO()
    chart.render_to_png(file_obj, dpi=dpi, **kwargs)
    file_obj.seek(0)
    return web.Response(body=file_obj.read(), content_type='image/png')
