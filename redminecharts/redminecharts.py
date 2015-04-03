from collections import defaultdict
from os.path import dirname

from flask import Config, Blueprint, request
from redmine import Redmine
import pygal


redminecharts = Blueprint(__name__, 'redminecharts')

config = Config(dirname(__file__))
config.from_pyfile('default.cfg')
config.from_pyfile('settings.cfg')

redmine = Redmine(config['REDMINE_URL'], key=config['API_KEY'])
issue_statuses = list(redmine.issue_status.all())


@redminecharts.route('/overall_issues')
def overall_issues():
    project_id = request.args.get('project_id', type=int)

    issues_by_statuses = defaultdict(int)
    for status in issue_statuses:
        rs = redmine.issue.filter(project_id=project_id, status_id=status.id,
                                  limit=1)
        list(rs)  # Execute request
        issues_by_statuses[status.name] = rs.total_count

    pie = pygal.Pie(style=config['PYGAL_STYLE'])
    for key, value in sort_by_value(issues_by_statuses, reverse=True):
        pie.add(key, value)
    return pie.render_response()


def sort_by_value(mapping, **kwargs):
    return sorted(mapping.iteritems(), key=lambda (_, v): v,
                  **kwargs)
