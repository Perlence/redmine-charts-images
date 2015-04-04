from io import BytesIO
from os.path import dirname

import arrow
from flask import Config, Blueprint, request, send_file
import pygal
from redmine import Redmine


redminecharts = Blueprint(__name__, 'redminecharts')

config = Config(dirname(__file__))
config.from_pyfile('default.cfg')
config.from_pyfile('settings.cfg')

pygal_config = pygal.Config(style=config['PYGAL_STYLE'])

redmine = Redmine(config['REDMINE_URL'], key=config['API_KEY'])
issue_statuses = list(redmine.issue_status.all())


@redminecharts.route('/issues_by_status', methods=['GET'])
def issues_by_status():
    project_id = request.args.get('project_id', type=int)

    issues_by_status = {}
    for status in issue_statuses:
        rs = redmine.issue.filter(project_id=project_id, status_id=status.id,
                                  limit=1)
        list(rs)  # Execute request
        issues_by_status[status.name] = rs.total_count

    chart = pygal.Pie(pygal_config)
    for key, value in sort_by_value(issues_by_status, reverse=True):
        chart.add('{} ({})'.format(key, value), value)
    return render_png_response(chart)


@redminecharts.route('/issues_per_frame', methods=['GET'])
def issues_per_frame():
    now = arrow.get()
    project_id = request.args.get('project_id', type=int)
    start = request.args.get('start', type=arrow.get,
                             default=now.floor('year'))
    end = request.args.get('end', type=arrow.get,
                           default=now)
    frame = request.args.get('frame', default='month')

    issues_per_month = {}
    date_range = arrow.Arrow.range(frame, start, end)
    for s in date_range:
        e = min(s.ceil(frame), end)
        query = '><{:YYYY-MM-DD}|{:YYYY-MM-DD}'.format(s, e)
        created = redmine.issue.filter(
            project_id=project_id, status_id='*', created_on=query, limit=1)
        closed = redmine.issue.filter(
            project_id=project_id, status_id='closed', closed_on=query,
            limit=1)
        list(created)
        list(closed)
        issues_per_month[s] = {
            'Created': created.total_count,
            'Closed': closed.total_count,
        }

    chart = pygal.Bar(pygal_config)
    chart.x_labels = [format(d, 'MMM/YY') for d in date_range]
    for name in ('Created', 'Closed'):
        chart.add(name, [issues_per_month[d][name] for d in date_range])
    return render_png_response(chart)


@redminecharts.route('/today_issues', methods=['GET'])
def today_issues():
    project_id = request.args.get('project_id', type=int)

    today = arrow.get().format('YYYY-MM-DD')
    created = redmine.issue.filter(
        project_id=project_id, status_id='*', created_on=today, limit=1)
    closed = redmine.issue.filter(
        project_id=project_id, status_id='closed', closed_on=today, limit=1)
    list(created)
    list(closed)

    chart = pygal.Bar(pygal_config)
    chart.add('Created', created.total_count)
    chart.add('Closed', closed.total_count)
    return render_png_response(chart)


def sort_by_key(mapping, **kwargs):
    return sorted(mapping.iteritems(), key=lambda (k, _): k, **kwargs)


def sort_by_value(mapping, **kwargs):
    return sorted(mapping.iteritems(), key=lambda (_, v): v, **kwargs)


def render_png_response(chart, dpi=72, **kwargs):
    file_obj = BytesIO()
    chart.render_to_png(file_obj, dpi=dpi, **kwargs)
    file_obj.seek(0)
    return send_file(file_obj, mimetype='image/png')
