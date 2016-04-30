# -*- coding: utf-8  -*-

import oursql, os

def get(args):
    if u'event' in args and u'year' in args and u'country' in args:
        queryArgs = (u'Images_from_Wiki_Loves_{event}_{year}_in_{country}'.format(**args),)
    else:
        return
    start = 'start' in args and args.get('start').isdigit() and int(args.get('start')) or 0
    params = {}
    params['user'] =  u' AND img_user_text = ?' if u'user' in args else u''
    if 'user' in params:
        queryArgs += (args['user'],)
    params['start'] =  ' OFFSET ' + str(args.get('start')) if start else u''
    params['mb'] = minmax(args.get('minmb'), args.get('maxmb'), ' AND img_size', lambda n:int(n) * 1048576)
    params['mp'] = minmax(args.get('minmp'), args.get('maxmp'), ' HAVING pixels', lambda n:int(n) * 1000000)
    params['timestamp'] = minmax(args.get('from'), args.get('until'), ' AND img_timestamp', lambda n:len(n) == 14 and n)
    conn = connection = oursql.connect(db='commonswiki_p', host='s4.labsdb',
            read_default_file=os.path.expanduser('~/replica.my.cnf'))
    c = conn.cursor()
    c.execute(u'''SELECT
 img_name,
 SUBSTR(MD5(img_name), 1, 2),
 img_width,
 img_height,
 (img_width * img_height) pixels,
 img_size,
 img_timestamp
 FROM categorylinks
 INNER JOIN page ON cl_from = page_id
 INNER JOIN image ON page_title = img_name
 WHERE cl_to = ? AND cl_type = 'file' AND img_major_mime = 'image'{user}{timestamp}{mb}{mp}
 ORDER BY pixels DESC
 LIMIT 201{start}'''.format(**params), (args['cat'].replace(u'+', u'_'),))
    imgs = [(i[0].decode('utf-8'), i[1], int(i[2]), int(i[3]), i[4], i[5], i[6]) for i in c.fetchall()]
    return imgs

def minmax(pmin, pmax, prefix, func=None):
    pmin = (func(pmin) if func else pmin) if pmin and pmin.isdigit() else ''
    pmax = (func(pmax) if func else pmax) if pmax and pmax.isdigit() else ''
    if pmin:
        if pmax: expr = ' BETWEEN {} AND {}'.format(pmin, pmax)
        else: expr = ' >= {}'.format(m[0])
    else:
        if pmin: expr = ' <= {}'.format(m[1])
        else: expr = ''
    return expr and prefix + expr
