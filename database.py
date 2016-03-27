#!/usr/bin/python
# -*- coding: utf-8 -*-

import re, json, sys, time
import oursql, os
from collections import defaultdict
from urllib import urlopen

updateLog = []

class DB:
    """
    Classe para fazer consultas ao banco de dados
    """
    def __init__(self):
        self.connect()
    def connect(self):
        self.conn = oursql.connect(db='commonswiki_p', host='commonswiki.labsdb',
            read_default_file=os.path.expanduser('~/replica.my.cnf'),
            read_timeout=10, charset='utf8', use_unicode=True, autoping=True)
        self.cursor = self.conn.cursor()
    def query(self, *sql):
        """
        Tenta fazer a consulta, reconecta até 10 vezes até conseguir
        """
        loops = 0
        while True:
            try:
                self.cursor.execute(*sql)
            except (AttributeError, oursql.OperationalError):
                if loops < 10:
                    loops += 1
                    print 'Erro no DB, esperando %ds antes de tentar de novo' % loops
                    time.sleep(loops)
                else:
                    self.cursor.execute(*sql)
                    break
            else:
                break
    def get(self):
        return self.cursor.fetchall()

def reData(txt, year):
    """
    Parser para linha da configuração
    """
    m = re.search(ur'''
        \s*wl\["(?P<event>earth|monuments)"\]\[(?P<year>20\d\d)]\ ?=\ ?\{|
        \s*\["(?P<country>[-a-z]+)"\]\ =\ \{\["start"\]\ =\ (?P<start>%s\d{10}),\ \["end"\]\ =\ (?P<end>%s\d{10})\}
        ''' % (year, year), txt, re.X)
    return m and m.groupdict()


def getConfig(page):
    """
    Lê a configuração da página de configuração no Commons
    """
    api = urlopen('https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=revisions&titles=%s&rvprop=content' % page)
    text = json.loads(api.read())['query']['pages'].values()[0]['revisions'][0]['*']
    
    data, event, prefixes = {}, None, {}
    lines = iter(text.split(u'\n'))
    for l in lines:
        m = re.search(u'\s*\["(?P<prefix>[\w-]+)"\] = "(?P<name>[\w ]+)"|(?P<close>\})', l)
        if prefixes and m and m.group('close'):
            break
        elif m and m.group('prefix'):
            prefixes[m.group('prefix')] = m.group('name')

    for l in lines:
        g = reData(l, event[-4:] if event else ur'20\d\d')
        if not g:
            continue
        if g['event']:
            event = g['event'] + g['year']
            data[event] = {}
        elif g['country'] and event:
            if g['country'] not in prefixes:
                updateLog.append(u'Unknow prefix: ' + g['country'])
                continue
            data[event][prefixes[g['country']]] = {'start': int(g['start']), 'end': int(g['end'])}

    return {name: config for name, config in data.items() if config}

catExceptions = {
    u'Netherlands': u'the_Netherlands',
    u'Czech Republic': u'the_Czech_Republic',
    u'Philippines': u'the_Philippines',
    u'United Kingdom': u'the_United_Kingdom',
    u'United States': u'the_United_States'
}

dbquery = u'''SELECT
 img_timestamp,
 img_name IN (SELECT DISTINCT gil_to FROM globalimagelinks),
 user_name,
 user_registration
 FROM (SELECT
   cl_to,
   cl_from
   FROM categorylinks
   WHERE cl_to = ? AND cl_type = 'file') cats
 INNER JOIN page ON cl_from = page_id
 INNER JOIN image ON page_title = img_name
 INNER JOIN user ON img_user = user_id'''

def getData(name, data):
    """
    Coleta dados do banco de dados e processa
    """
    category = u'Images_from_Wiki_Loves_%s_%s_in_' % \
            (name[0:-4].capitalize(), name[-4:])

    starttime = min(data[c]['start'] for c in data if 'start' in data[c])
    endtime = max(data[c]['end'] for c in data if 'end' in data[c])

    for country in data.keys():
        if country[0].islower():
            updateLog.append(u'')
        cat = category + catExceptions.get(country, country.replace(' ', u'_'))
        if name == 'monuments2010':
            cat = u'Images_from_Wiki_Loves_Monuments_2010'
        commonsdb.query(dbquery, (cat,))

        dbData = tuple(
            (int(timestamp),
             bool(usage),
             user.decode('utf-8'),
             int(user_reg or 0))
            for timestamp, usage, user, user_reg in commonsdb.get())

        if not dbData:
            updateLog.append(u'%s in %s is configurated, but no file was found in [[Category:%s]]' %
                             (name, country, cat.replace(u'_', u' ')))
            del data[country]
            continue

        cData = {'starttime': data[country].get('start', starttime),
                 'endtime': data[country].get('end', endtime),
                 'data': defaultdict(int), # data: {timestamp_day0: n, timestamp_day1: n,...}
                 'users': {}} # users: {'user1': {'count': n, 'usage': n, 'reg': timestamp},...}

        for timestamp, usage, user, user_reg in dbData:
            # Desconsidera timestamps fora do período da campanha
            if not cData['starttime'] <= timestamp <= cData['endtime']:
                continue
            # Conta imagens por dia
            cData['data'][str(timestamp)[0:8]] += 1
            if user not in cData['users']:
                cData['users'][user] = {'count': 0, 'usage': 0, 'reg': user_reg}
            cData['users'][user]['count'] += 1
            if usage:
                cData['users'][user]['usage'] += 1

        data.setdefault(country, {}).update(
            {'data': cData['data'], 'users': cData['users']})
        data[country]['usercount'] = len(cData['users'])
        data[country]['count'] = sum(u['count'] for u in cData['users'].itervalues())
        data[country]['usage'] = sum(u['usage'] for u in cData['users'].itervalues())
        data[country]['category'] = cat

    return data


if __name__ == '__main__' and 'update' in sys.argv:
    config = getConfig(u'Module:WL_data')
    try:
        with open('db.json', 'r') as f:
            db = json.load(f)
    except Exception as e:
        print u'Erro ao abrir db.json:', repr(e)
        db = {}

    commonsdb = DB()
    for WL in config:
        starttime = min(config[WL][c]['start'] for c in config[WL] if 'start' in config[WL][c])
        endtime = max(config[WL][c]['end'] for c in config[WL] if 'end' in config[WL][c])
        # Só atualiza concursos que não estejam no db.json ou que estejam em andamento
        if WL not in db or starttime < time.strftime('%Y%m%d%H%M%S') < endtime:
            start = time.time()
            db[WL] = getData(WL, config[WL])
            with open('db.json', 'w') as f:
                json.dump(db, f)
            log = 'Saved %s: %dsec, %d countries, %d uploads' % \
                (WL, time.time() - start, len(db[WL]), sum(db[WL][c].get('count', 0) for c in db[WL]))
            print log
            updateLog.append(log)
    commonsdb.conn.close()
    if updateLog:
        with open('update.log', 'w') as f:
            f.write(time.strftime('%Y%m%d%H%M%S') + '\n' + '\n'.join(updateLog))
