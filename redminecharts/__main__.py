from gevent import monkey
monkey.patch_all()

from flask import Flask

from redminecharts import redminecharts


app = Flask(__name__)
app.register_blueprint(redminecharts)
app.run('127.0.0.1', debug=True)
