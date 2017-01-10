#!/usr/bin/python
# -*- coding: utf-8  -*-

from flask import Flask, render_template, request, make_response
import json, os, time, re
from os.path import getmtime
import images

app = Flask(__name__)
app.debug = True

dbtime = None

def loadDB():
    global db, menu, mainData, cData, dbtime
    mtime = getmtime('db.json')
    if dbtime and dbtime == mtime:
        return
    dbtime = mtime
    try:
        with open('db.json', 'r') as f:
            db = json.load(f)
    except:
        db = None
    menu = {name: sorted(e[-4:] for e in db if e[:-4] == name) for name in set(e[:-4] for e in db)}
    mainData = {name: {e[-4:]:
        {'count': sum(db[e][c]['count'] for c in db[e]), 
         'usercount': sum(db[e][c]['usercount'] for c in db[e]),
         'userreg': sum(db[e][c]['userreg'] for c in db[e]),
         'usage': sum(db[e][c]['usage'] for c in db[e])}
        for e in db if e[:-4] == name} for name in set(e[:-4] for e in db)}
    cData = {}
    for e in db:
        for c in db[e]:
            cData.setdefault(c, {}).setdefault(e[:-4], {}).update({e[-4:]: {
                'count': db[e][c]['count'], 'usercount': db[e][c]['usercount'],
                'usage': db[e][c]['usage'], 'userreg': db[e][c]['userreg']}})

loadDB()

@app.route('/')
def index():
    countries = {c: [(cData[c]['earth'].keys() if 'earth' in cData[c] else None),
                     (cData[c]['monuments'].keys() if 'monuments' in cData[c] else None),
                     (cData[c]['africa'].keys() if 'africa' in cData[c] else None)]
            for c in cData}
    return render_template('mainpage.html', title=u'Wiki Loves Competitions Tools', menu=menu,
            data=mainData, countries=countries)

@app.route('/log')
def logpage():
    try:
        with open('update.log', 'r') as f:
            log = f.read()
        timestamp = time.strftime('%H:%M, %d %B %Y', time.strptime(log[:14], '%Y%m%d%H%M%S'))
        log = re.sub(ur'\[\[([^]]+)\]\]', lambda m: u'<a href="https://commons.wikimedia.org/wiki/%s">%s</a>' %
                (m.group(1).replace(u' ', u'_'), m.group(1)), log[15:]).split(u'\n')
    except:
        log = timestamp = None
    return render_template('log.html', title=u'Update log', menu=menu, time=timestamp, log=log)

@app.route('/monuments', defaults={'name': 'monuments'})
@app.route('/earth', defaults={'name': 'earth'})
@app.route('/africa', defaults={'name': 'africa'})
def event_main(name):
    if not db:
        return index()
    if name in mainData:
        eventName = u'Wiki Loves %s' % name.capitalize()
        eventData = {name: {y: v for y, v in mainData[name].iteritems()}}
        eventData.update(countries = {c: cData[c][e] for c in cData
            for e in cData[c] if e == name})
        return render_template('eventmain.html', title=eventName, menu=menu, name=name, data=eventData)
    else:
        return render_template('page_not_found.html', title=u'Event not found', menu=menu)

@app.route('/monuments/20<year>', defaults={'name': 'monuments'})
@app.route('/earth/20<year>', defaults={'name': 'earth'})
@app.route('/africa/20<year>', defaults={'name': 'africa'})
def event_year(name, year):
    loadDB()
    if not db:
        return index()
    year = '20' + year
    event = name + year
    if event in db:
        eventName = u'Wiki Loves %s %s' % (name.capitalize(), year)
        eventData = {c: {d: db[event][c][d] for d in db[event][c] if d != 'users'} for c in db[event]}
        return render_template('event.html', title=eventName, menu=menu, name=name, year=year,
                               data=eventData, rickshaw=True)
    else:
        return render_template('page_not_found.html', title=u'Event not found', menu=menu)

@app.route('/monuments/20<year>/<country>', defaults={'name': 'monuments'})
@app.route('/earth/20<year>/<country>', defaults={'name': 'earth'})
@app.route('/africa/20<year>/<country>', defaults={'name': 'africa'})
def users(name, year, country):
    if not db:
        return index()
    year = '20' + year
    event = name + year
    if event in db and country in db[event]:
        eventName = u'Wiki Loves %s %s in %s' % (name.capitalize(), year, country)
        eventUsers = sorted(db[event][country]['users'].items(), key=lambda i: (i[1]['count'], i[0]), reverse=True)
        return render_template('users.html', title=eventName, menu=menu, name=name, year=year,
                               country=country, data=eventUsers, starttime=db[event][country]['start'])
    elif event in db:
        return render_template('page_not_found.html', title=u'Country not found', menu=menu)
    else:
        return render_template('page_not_found.html', title=u'Event not found', menu=menu)

@app.route('/country/<name>')
def country(name):
    if name in cData:
        return render_template('country.html', title=u'Wiki Loves Competitions in ' + name, menu=menu,
                data=cData[name], country=name)
    else:
        return render_template('page_not_found.html', title=u'Country not found', menu=menu)

@app.route('/images')
def images_page():
    args = dict(request.args.items())
    imgs = images.get(args)
    if not imgs:
        return render_template('images_not_found.html', menu=menu, title=u'Images not found')
    backto = [args['event'], args['year']] + ([args['country']] if 'user' in args else [])
    title = u'Images of %sWiki Loves %s %s in %s' % (args['user'] + u' in ' if 'user' in args else u'',
        args['event'].capitalize(), args['year'], args['country'])
    return render_template('images.html', menu=menu, title=title, images=imgs, backto=backto)

@app.route('/db.json')
def download():
    response = make_response(json.dumps(db))
    response.headers["Content-Disposition"] = "attachment; filename=db.json"
    response.headers["Content-type"] = "application/json"
    return response

@app.template_filter(name='date')
def date_filter(s):
    if type(s) == int:
        s = str(s)
    return '%s.%s.%s' % (s[6:8], s[4:6], s[0:4])

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html', title=u'Page not found', menu=menu), 404

if __name__ == '__main__':
    if os.uname()[1].startswith('tools-webgrid'):
        from flup.server.fcgi_fork import WSGIServer
        WSGIServer(app).run()
    else:
        # Roda fora do Labs
        app.run()
