# -*- coding: utf-8  -*-

from flask import Flask, render_template
import json, os

app = Flask(__name__)
app.debug = True

try:
    with open('db.json', 'r') as f:
        db = json.load(f)
except:
    db = None

@app.route('/')
def index(page=None):
    return render_template('mainpage.html', title=u'Wiki Loves Competitions Tools',
                           events=db.keys() if db else None)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html', title=u'Page not found'), 404

if __name__ == '__main__':
    if os.uname()[1].startswith('tools-webgrid'):
        from flup.server.fcgi_fork import WSGIServer
        WSGIServer(app).run()
    else:
        # Roda fora do Labs
        app.run()
