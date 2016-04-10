function renderLine (id, series) {
    var days = [];
    unique = function(v){return days.indexOf(v) == -1}
    for (var c = 0; c < series.length; c++) days = days.concat(Object.keys(series[c].data).filter(unique));
    days.sort();

    for (var country = 0; country < series.length; country++){
        var newData = [], dayY = 0;
        for (var i = 0; i < days.length; i++) {
            unix_timestamp = Date.UTC(days[i].substr(0, 4), days[i].substr(4, 2), days[i].substr(6, 2))/1000;
            if (series[country].data.hasOwnProperty(days[i])) dayY += series[country].data[days[i]];
            newData.push({x: unix_timestamp, y: dayY});
        }
        series[country].data = newData;
    }
    var graph = new Rickshaw.Graph({
        element: document.getElementById(id),
        width: 800,
        height: 500,
        renderer: 'line',
        stroke: true,
        preserve: true,
        series: series
    });
    graph.render();
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var hoverDetail = new Rickshaw.Graph.HoverDetail({
        graph: graph,
        xFormatter: function(x){
            var d = new Date(x * 1000);
            return d.getUTCDate() + ' ' + months[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
        },
        yFormatter: function(y){return y}
    });
    var yAxis = new Rickshaw.Graph.Axis.Y({graph: graph});
    yAxis.render();
    var xAxis = new Rickshaw.Graph.Axis.Time({graph: graph});
    xAxis.render();
}
function renderBar(name, id, series){
    var c1 = name == 'earth' ? '#339966' : '#8F0000';
    var c2 = name == 'earth' ? '#45E695' : '#E62E2E';
    var ticks = [];
    var width = Math.min(800, series.length * 200);
    var height = 200;
    var theight = height + 17
    var maxh = Math.max.apply(null, series.map(function(v){return v.count}));
    var graph = '<svg width="' + width + '" height="' + theight + '">';
    var w = width / series.length;
    var rect = function(x, h, color){
        return '<rect x="' + w * x + '" y="' + height * (1 - h / maxh) + '" width="' + Math.floor(w / 4) + 
            '" height="' + height * h / maxh + '" fill="' + color + '"/>'
    };
    for (var year = 0; year < series.length; year++){
        graph += rect(year + 0.1, series[year].count, c1);
        graph += rect(year + 0.2, series[year].usage , c2);
        graph += rect(year + 0.5, series[year].usercount, '#2266AA');
        graph += rect(year + 0.6, series[year].userreg, '#5CA3E6');
        ticks.push(series[year].year);
    }
    var xAxis = '';
    for (var y = 0; y < ticks.length; y++){
        xAxis += '<text x="' + String(Math.floor((y + 0.5) * width / ticks.length)) + '" y="' + theight + '" text-anchor="middle">' + ticks[y] + '</text>';
    }
    document.getElementById(id).innerHTML += graph + xAxis + '</svg>';
}

function countryLine(d, i){
    line = [];
    line.push('<td><span style="display:inline-block; width:40px; height:2px; border-top:4px solid ' +
        data[d].series[i].color + '"></span></td>');
    var countryLink = location.pathname.split('/').slice(0, -2).concat('country', data[d].series[i].name).join('/')
    line.push('<td style="background-color:#F8F8F8"><a href="' + countryLink + '">' +
        data[d].series[i].name + '</a></td>');
    line.push('<td>' + String(data[d].series[i].count) + '</td>');
    line.push('<td style="background-color:#F8F8F8">' + String(data[d].series[i].usage) + ' (' +
        String(Math.round(100 * data[d].series[i].usage / data[d].series[i].count)) + '%)</td>');
    line.push('<td><a href="' + location.pathname + '/' + data[d].series[i].name.replace(/ /g, '_') + '">' +
        String(data[d].series[i].usercount) + '</a></td>');
    line.push('<td style="background-color:#F8F8F8">' + String(data[d].series[i].userreg) + ' (' +
        String(Math.round(100 * data[d].series[i].userreg / data[d].series[i].usercount)) + '%)</td>');
    return '<tr>' + line.join('') + '</tr>'
}

window.onload = function(){
    if (typeof data === 'undefined') return;
    var countries = document.getElementById('countries');
    if (countries) palette = new Rickshaw.Color.Palette({scheme: 'munin'});
    for (var d = 0; d < data.length; d++){
        if (countries){
            for (var i = 0; i < data[d].series.length; i++){
                data[d].series[i]['color'] = palette.color(i);
            }
            data[d].series.sort(function(a, b){return b.count - a.count});
            for (var i = 0; i < data[d].series.length; i++) countries.innerHTML += countryLine(d, i);
        }
        if (data[d].type == 'line') renderLine(data[d].id, data[d].series);
        else if (data[d].type == 'bar') renderBar(data[d].name, data[d].id, data[d].series);
    }
}
