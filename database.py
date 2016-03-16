#!/usr/bin/python
# -*- coding: utf-8 -*-

import re, codecs, json, sys
import oursql, os
#from urllib import urlopen

def conn():
    """
    Conecta ao banco de dados do commons
    """
    connection = oursql.connect(db='commonswiki_p', host='commonswiki.labsdb',
                                read_default_file=os.path.expanduser('~/replica.my.cnf'),
                                read_timeout=10, charset='utf8', use_unicode=True)
    return connection.cursor()

class Event:
    """
    Classe para consultar e processar dados sobre os eventos
    """
    def __init__(self, config):
        """
        Lê configuração do evento ao criar uma instância
        """
        self.name = config['name']
        self.cat = config['category'].replace(u' ', u'_')
        self.starttime = config['starttime']
        self.endtime = max(config['endtime'].values())
        self.countries = dict(((name, {'endtime': endtime})
                               for name, endtime in config['endtime'].items()))

    def uploadCount(self):
        """
        Contador de uploads
        TODO: Desconsiderar uploads antes de starttime
        """
        c.execute(u'''SELECT
 SUBSTR(cl_to, 38) país,
 UNIX_TIMESTAMP(SUBSTR(img_timestamp, 1, 8)) dia,
 SUBSTR(img_timestamp, 1, 10) hora,
 COUNT(*) upload
 FROM categorylinks
 INNER JOIN page ON cl_from = page_id
 INNER JOIN image ON page_title = img_name AND img_timestamp < ?
 WHERE cl_type = 'file' AND cl_to IN (SELECT
   page_title
   FROM page
   WHERE page_namespace = 14 AND page_title LIKE ? AND page_title NOT LIKE '%\_-\_%'
 )
 GROUP BY país, hora''', (self.endtime, self.cat + 'in_%'))
        
        # Lê o resultado da query
        r = [(country.decode('utf-8').replace(u'_', u' '), int(day) + 86400, int(hour), int(count))
             for country, day, hour, count in c.fetchall()]
        # Considera apenas até endtime de cada país e desconsidera países que não estão na configuração
        r = [(country, day, count) for country, day, hour, count in r
             if country in self.countries and hour <= self.countries[country]['endtime']]
        # Agrupa por país e dia, somando as contagens por hora de cada dia
        r = [(d[0], d[1], sum(h[2] for h in r if (h[0], h[1]) == d)) for d in set((i[0], i[1]) for i in r)]

        for country in self.countries:
            data = []
            y = 0
            for rcountry, day, count in sorted(r):
                if rcountry == country:
                    y += count
                    data.append((day, y))
            self.countries[country]['data'] = u', '.join(u'{x:%d,y:%d}' % (x, y) for x, y in data)

    def imgUsage(self):
        """
        Uso das imagens nas wikis
        """
        c.execute(u'''SELECT
 SUBSTR(cl_to, 38) country,
 SUM(img_name IN (SELECT DISTINCT gil_to FROM globalimagelinks)) use_in_wiki
 FROM categorylinks INNER JOIN page ON cl_from = page_id INNER JOIN image ON page_title = img_name
 WHERE cl_type = 'file' AND cl_to IN (SELECT
   page_title
   FROM page
   WHERE page_namespace = 14 AND page_title LIKE ? AND page_title NOT LIKE '%\_-\_%')
 GROUP BY country''', (self.cat + 'in_%',))
        r = dict((country.decode('utf-8').replace(u'_', u' '), int(usage)) for country, usage in c.fetchall())
        for country in self.countries:
            self.countries[country]['usage'] = r[country] if country in r else 0

    def uploadUserCount(self):
        """
        Número de usuários que fizeram upload
        TODO: Incluir starttime na query
        """
        c.execute(u'''SELECT
 country,
 COUNT(*),
 SUM(user_registration > 20140501000000)
 FROM (SELECT DISTINCT
   SUBSTR(cl_to, 38) country,
   img_user
   FROM categorylinks INNER JOIN page ON cl_from = page_id INNER JOIN image ON page_title = img_name
   WHERE cl_type = 'file' AND cl_to IN (SELECT
     page_title
     FROM page
     WHERE page_namespace = 14 AND page_title LIKE ? AND page_title NOT LIKE '%\_-\_%')
   ) users
 INNER JOIN user ON img_user = user_id
 GROUP BY country;''', (self.cat + 'in_%',))
        r = dict((country.decode('utf-8').replace(u'_', u' '), u'[%d,%d]' % (int(count), int(reg)))
                 for country, count, reg in c.fetchall())
        for country in self.countries:
            self.countries[country]['users'] = r[country] if country in r else u'[0,0]'

    def usersList(self, country):
        """
        Usuários que fizeram upload por país
        """
        c.execute(u'''SELECT
 user_name,
 c,
 use_in_wiki,
 user_registration
 FROM (SELECT
   img_user,
   COUNT(*) c,
   SUM(img_name IN (SELECT DISTINCT gil_to FROM globalimagelinks)) use_in_wiki
   FROM categorylinks INNER JOIN page ON cl_from = page_id INNER JOIN image ON page_title = img_name
   WHERE cl_to = ? AND cl_type = 'file'
   GROUP BY img_user
   ORDER BY c DESC
  ) img
 INNER JOIN user ON img_user = user_id''', ( self.cat + u'_in_' + country.replace(u' ', u'_'),))
        r = [(user.decode('utf-8').replace(u'_', u' '), int(count), int(usage),
              u'%s/%s/%s' % (str(reg)[6:8], str(reg)[4:6], str(reg)[0:4]) if reg else u'?')
             for user, count, usage, reg in c.fetchall()]
        return r

    def getMain(self):
        """
        Faz as consultas para página principal do evento e retorna os dados
        """
        self.uploadCount()
        self.imgUsage()
        self.uploadUserCount()

        main = u',\n  '.join(
            u'{{name:"{name}", usage:{usage}, users:{users}, endtime:"{endtime}", data:[{data}]}}' \
                .format(name=country, **self.countries[country]) for country in self.countries)
        return main

    def getAll(self):
        """
        Faz todas as consultas do evento e retorna os dados
        """
        r = {}
        r['main'] = self.getMain()
        for country in self.countries:
            r[country] = self.usersList(country)
        return r

if __name__ == '__main__' and 'update' in sys.argv:
    #TODO: Ler a página de configuração do commons
    print os.getcwd()
    with codecs.open('config.json', 'r', 'utf-8') as f:
        config = json.load(f)
    try:
        with open('db.json', 'r') as f:
            db = json.load(f)
    except Exception as e:
        print u'Erro ao abrir db.json:', repr(e)
        db = {}

    c = conn()
    for WL in config:
        event = Event(config[WL])
        db.setdefault(WL, {})['main'] = event.getMain()
        print WL, 'updated'

    with open('db.json', 'w') as f:
        json.dump(db, f)
