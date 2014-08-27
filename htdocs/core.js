/**
*
* DB GUI
* v190514
*
*/
/**
*
*
* ============================================================================================================================================================================================================
*
*/
// common flags, settings and object for their storage
var _tilde = {};
_tilde.debug_regime = false; // major debugging switch
_tilde.demo_regime = false;
_tilde.degradation = false;
_tilde.hashes = [];
_tilde.rendered = {}; // datahash : bool, ...
_tilde.tab_buffer = []; // tab_name, ...
_tilde.last_request = false; // todo: request history dispatcher
_tilde.last_browse_request = false; // todo: request history dispatcher
_tilde.socket = null;
_tilde.freeze = false;
_tilde.wsock_delim = '~#~#~';
_tilde.cur_anchor = false;
_tilde.multireceive = 0;
_tilde.filetree = {};
_tilde.filetree.transports = [];
_tilde.filetree.root = '';
_tilde.filetree.load_msg = 'Requesting directory listing...';
_tilde.busy_msg = 'Program core is now busy serving your request. Please, wait a bit and try again.';
_tilde.cwidth = 0;
_tilde.cinterval = null;
_tilde.connattempts = 0;
_tilde.maxconnattempts = 5;
_tilde.plots = [];
_tilde.last_chkbox = null;

// units
_tilde.units = {
    'energy': {'au':0.03674932601, 'eV':1, 'Ry':0.07349861206},
    'phonons': {'cm<sup>-1</sup>':1, 'THz':0.029979}
};
_tilde.unit_capts = {'energy':'Energy', 'phonons':'Phonon frequencies'};
_tilde.default_settings = {};
_tilde.default_settings.units = {'energy':'eV', 'phonons':'cm<sup>-1</sup>'};
_tilde.default_settings.cols = [1, 1002, 7, 25, 17, 9, 10, 12, 22]; // these are cid's of hierarchy API (cid>1000 means specially defined column)
_tilde.default_settings.colnum = 100;
_tilde.default_settings.objects_expand = true;

// IE indexOf()
if (!Array.prototype.indexOf){
    Array.prototype.indexOf = function(obj, start){
    for (var i = (start || 0), j = this.length; i < j; i++){
        if (this[i] === obj) { return i; }
    }
    return -1;
    }
}
/**
*
*
* ============================================================================================================================================================================================================
*
*/
// ERRORS BOX
function notify(message, not_urgent) {
    if (typeof not_urgent == 'undefined') $('#notifybox').css('background-color', '#fc0');
    else $('#notifybox').css('background-color', '#9cc');
    $('#errormsg').empty();
    setTimeout(function(){ $('#errormsg').empty().append(message).parent().show(); }, 250);
}

// FILETREE FUNCTIONS
function showTree(elem, path, resourse_type){
    $(elem).addClass('wait');
    __send('list',  {path: path.toString(), transport:resourse_type} );
}
function bindTree(elem, resourse_type){
    $(elem).find('li a').click(function(e){
        if ( $(this).parent().hasClass('directory') ){
            if ( $(this).parent().hasClass('collapsed') ){
                $(this).parent().parent().find('ul').hide();
                $(this).parent().parent().find('li.directory').removeClass('expanded').addClass('collapsed');
                $(this).parent().find('ul').remove();
                showTree( $(this).parent(), $(this).attr('rel'), resourse_type );
            } else {
                $(this).parent().find('ul').hide();
                $(this).parent().removeClass('expanded').addClass('collapsed');
            }
        } else { // FILETREE FILE PROCESSOR
            var $el = $(this);
            if (!$el.hasClass('_done')){
                var rel = $el.attr("rel");
                __send('report',  {path: rel, directory: 0, transport:'local'} );
            }
        }
        return false;
    });
}

// UTILITIES
function __send(act, req, nojson){
    if (_tilde.debug_regime) logger('REQUESTED: '+act); // invalid for login TODO
    if (_tilde.freeze){ notify(_tilde.busy_msg); return; }
    if (!nojson) req ? req = JSON.stringify(req) : req = '';
    $('#loadbox').show();
    _tilde.freeze = true;

    // beware heavy and recursive requests!
    if ($.inArray(act, ["report", "restart", "clean", "login"])) _tilde.last_request = false; // todo: request history dispatcher
    else _tilde.last_request = act + _tilde.wsock_delim + req; // todo: request history dispatcher

    if (act == 'browse') _tilde.last_browse_request = req; // todo: request history dispatcher

    try{ _tilde.socket.send( act + _tilde.wsock_delim + req ) }
    catch(ex){ logger('AN ERROR WHILE SENDING DATA HAS OCCURED: '+ex) }
}

function logger(message, no_wrap, clean){
    if (!!clean) $("#debug").empty();
    if (!no_wrap) message = "<div>" + message.replace(/ /g, "&nbsp;") + "</div>";
    $("#debug").prepend(message);
}

function set_console(show){
    if (show) $('#console_holder').animate({ height: 'show' }, { duration: 250, queue: false });
    else $('#console_holder').animate({ height: 'hide' }, { duration: 250, queue: false });
}

function set_dbs(){
    $('#metablock').html( '<span class="link white">' + _tilde.settings.dbs[0] + '</span>' );

    var title = 'Current DB: ' + _tilde.settings.dbs[0];
    if (!!_tilde.settings.dbs.length && _tilde.settings.dbs.length > 1) title += ' (<span class=link>' + (_tilde.settings.dbs.length - 1) + ' more</span>)';
    $('h1').html( title );

    var options = '<option value="0" selected="selected">copy to ...</option>';
    $.each(_tilde.settings.dbs, function(n, item){
        if (n==0) return true;
        options += '<option value="' + item + '">copy to ' + item + '</option>';
    });
    $('#db_copy_select').empty().append(options);
}

function open_ipane(cmd, target){
    if (!!target) var current = $('#o_'+target+' ul.ipane_ctrl li[rel='+cmd+']');
    else var current = $('ul.ipane_ctrl li[rel='+cmd+']');
    if (!current.length) { notify('Error opening pane '+cmd+'!'); return; }

    current.parent().children('li').css('border-bottom-color', '#06c');
    current.css('border-bottom-color', '#fff').parent().parent().children( 'div.ipane' ).hide();
    current.parent().parent().find( 'div[rel='+cmd+']' ).show();

    if (_tilde.tab_buffer.indexOf(target+'_'+cmd) != -1) return;

    switch(cmd){
        case 'ph_dos':
        case 'e_dos':
        case 'ph_bands':
        case 'e_bands':
        case 'optstory':
        case 'estory':
            __send(cmd,  {datahash: target} );
            break;
        case 'vib':
            __send('phonons',  {datahash: target} );
            break;
    }
    _tilde.tab_buffer.push(target+'_'+cmd);
}

function redraw_vib_links( text2link, target ){
    $('#o_'+target+' td.ph_ctrl').each(function(){
        var $this = $(this);
        var linktxt = $this.text();
        if (!!text2link) $this.empty().append( '<span class=link>'+linktxt+'</span>' );
        else $this.empty().append( linktxt );
    });
    if (!!text2link){
        // attach vibration handler
        $('#o_'+target+' td.ph_ctrl span').click(function(){
            $('#o_'+target+' td.ph_ctrl span').removeClass('red');
            $(this).addClass('red');
            var phonons = '[' + $(this).parent().attr('rev') + ']';
            document.getElementById('f_'+target).contentWindow.vibrate_3D( phonons );
        });
    }
}

function close_obj_tab(tab_id){
    if (delete _tilde.rendered[tab_id] && $('#i_'+tab_id).next('tr').hasClass('obj_holder')) $('#i_'+tab_id).next('tr').remove();
    _tilde.tab_buffer = $.grep(_tilde.tab_buffer, function(val, index){
        if (val.indexOf(tab_id) == -1) return true;
    });
}

function iframe_download( request, scope, hash ){
    $('body').append('<form style="display:none;" id="data-download-form" action="/' + request + '/' + scope + '/' + hash + '" target="file-process" method="get"></form>');
    $('#data-download-form').submit().remove();
}

function e_plotter(req, plot, divclass, ordinate){
    var show_points = (divclass.indexOf('estory') !== -1) ? false : true;
    var plot = JSON.parse(plot);
    var options = {
        legend: {show: false},
        series: {lines: {show: true}, points: {show: show_points}, shadowSize: 3},
        xaxis: {labelHeight: 40, minTickSize: 1, tickDecimals: 0},
        yaxis: {color: '#eeeeee', labelWidth: 50},
        grid: {borderWidth: 1, borderColor: '#000', hoverable: true, clickable: true}
    };
    if (plot[0].data.length == 1) options.xaxis.ticks = []; // awkward EXCITING optimization

    var target = $('#o_'+req.datahash+' div.'+divclass);

    var cpanel = target.prev('div');
    cpanel.parent().removeClass('loading');

    $.plot(target, plot, options);
    $(target).bind("plotclick", function(event, pos, item){
        if (item) document.getElementById('f_'+req.datahash).contentWindow.location.hash = '#' + _tilde.settings.dbs[0] + '/' + req.datahash + '/' + item.dataIndex;
    });

    target.append('<div style="position:absolute;z-index:4;width:200px;left:40%;bottom:0;text-align:center;font-size:1.5em;background:#fff;">Step</div>&nbsp;');
    target.append('<div style="position:absolute;z-index:4;width:200px;left:0;top:300px;text-align:center;font-size:1.25em;transform:rotate(-90deg);transform-origin:left top;-webkit-transform:rotate(-90deg);-webkit-transform-origin:left top;-moz-transform:rotate(-90deg);-moz-transform-origin:left top;background:#fff;">'+ordinate+'</div>');
}

function dos_plotter(req, plot, divclass, axes){
    var plot = JSON.parse(plot);
    var options = {
        legend: {show: false},
        series: {lines: {show: true}, points: {show: false}, shadowSize: 0},
        xaxis: {color: '#eeeeee', labelHeight: 40},
        yaxis: {ticks: [], labelWidth: 30},
        grid: {borderWidth: 1, borderColor: '#000'}
    };

    var cpanel = $('#o_'+req.datahash+' div.'+divclass).prev('div');
    cpanel.parent().removeClass('loading');

    for (var i=0; i < plot.length; i++){
        cpanel.prepend('<input type="checkbox" name="' + plot[i].label + '" checked=checked id="cb_' + req.datahash + '_' + plot[i].label + '" rev="' + JSON.stringify(plot[i].data) + '" rel="'+plot[i].color+'" />&nbsp;<label for="cb_'+ req.datahash + '_' + plot[i].label +'" style="color:' + plot[i].color + '">' + plot[i].label + '</label>&nbsp;');
    }
    function plot_user_choice(){
        var data_to_plot = [];
        cpanel.find("input:checked").each(function(){
            var d = $(this).attr('rev');
            data_to_plot.push({color: $(this).attr('rel'), data: JSON.parse( $(this).attr('rev') )});
        });
        var target = $('#o_'+req.datahash+' div.'+divclass);
        $.plot(target, data_to_plot, options);

        target.append('<div style="position:absolute;z-index:14;width:200px;left:40%;bottom:0;text-align:center;font-size:1.5em;background:#fff;">'+axes.x+'</div>&nbsp;');
        target.append('<div style="position:absolute;z-index:14;width:200px;left:0;top:300px;text-align:center;font-size:1.5em;transform:rotate(-90deg);transform-origin:left top;-webkit-transform:rotate(-90deg);-webkit-transform-origin:left top;-moz-transform:rotate(-90deg);-moz-transform-origin:left top;background:#fff;">'+axes.y+'</div>');
    }
    cpanel.find("input").click(plot_user_choice);
    plot_user_choice();
    cpanel.children('div.export_plot').click(function(){ export_data(plot) });
}

function bands_plotter(req, plot, divclass, ordinate){
    var plot = JSON.parse(plot);
    var options = {
        legend: {show: false},
        series: {lines: {show: true}, points: {show: false}, shadowSize: 0},
        xaxis: {color: '#eeeeee', labelHeight: 40, font:{size: 9.5, color: '#000'}, labelAngle: 270},
        yaxis: {color: '#eeeeee', labelWidth: 50},
        grid: {borderWidth: 1, borderColor: '#000'}
    };

    var target = $('#o_'+req.datahash+' div.'+divclass);

    var cpanel = target.prev('div');
    cpanel.parent().removeClass('loading');

    options.xaxis.ticks = plot[0].ticks
    //options.xaxis.ticks[options.xaxis.ticks.length-1][1] = '' // avoid cropping in canvas
    $.plot(target, plot, options);

    target.append('<div style="position:absolute;z-index:14;width:200px;left:0;top:300px;text-align:center;font-size:1.25em;transform:rotate(-90deg);transform-origin:left top;-webkit-transform:rotate(-90deg);-webkit-transform-origin:left top;-moz-transform:rotate(-90deg);-moz-transform-origin:left top;background:#fff;">'+ordinate+'</div>');

    target.prev('div').children('div.export_plot').click(function(){ export_data(plot) });
}

function export_data(data){
    var ref = window.open('', 'export' + Math.floor(Math.random()*100));
    var dump = '';
    for (var j=0; j < data[0].data.length; j++){
        dump += data[0].data[j][0] + '\t';
        for (var i=0; i < data.length; i++){
            dump += data[i].data[j][1] + '\t';
        }
        dump += '\n';
    }
    ref.document.body.innerHTML = '<pre>' + dump + '</pre>';
}

function add_tag_expanders(){
    if (!$('#splashscreen_holder').is(':visible')) return;
    $('a.tagmore, a.tagless').remove();
    $('div.tagarea').each(function(){
        if ($(this).find('a.visibletag').length > 20){
            $(this).prepend('<a class=tagmore href=#>&rarr;</a>');
            $(this).addClass('tagarea_reduced');
        } else {
            $(this).removeClass('tagarea_reduced');
        }
    });
}

function switch_menus(which){
    $('div.menu_cmds').hide();
    if (!which) $('#menu_main_cmds').show();
    else if (which == 1) $('#menu_row_cmds').show();
    else if (which == 2) $('#menu_col_cmds').show();
}

function gather_tags(area, myself){
    var found_tags = [];

    if (myself){
        if (myself.hasClass('activetag')){
            myself.removeClass('activetag');
        } else {
            found_tags.push( myself.attr('rel') );
        }
    }
    area.find('a.activetag').each(function(){
        found_tags.push( $(this).attr('rel') );
    });

    return found_tags;
}

function remdublicates(arr){
    var i, len=arr.length, out=[], obj={};
    for (i=0;i<len;i++){
        obj[arr[i]]=0;
    }
    for (i in obj){
        out.push(i);
    }
    return out;
}

function gather_plots_data(){
    var data = [], ids = [];
    for (var j=0; j < _tilde.plots.length; j++){
        data.push([]);
        $('#databrowser td[rel='+_tilde.plots[j]+']').each(function(index){
            var t = $(this).text();
            if (t.indexOf('x') != -1){
                // special case of k-points
                var s = t.split('x'), t = 1;
                for (var i=0; i<s.length; i++){ t *= parseInt(s[i]) }
            } else if (t.indexOf(',') != -1) {
                // special case of tilting
                if (t.indexOf('biel') == -1){ // TODO!
                    var s = t.split(',');
                    for (var i=0; i<s.length; i++){ s[i] = parseFloat(s[i]) }
                    t = Math.max.apply(null, s);
                }
            }else {
                // non-numerics
                t = t.replace(/[^0-9\.\-]+/g, '');
                if (!t.length) t=0;
            }
            data[data.length-1].push(t);
            if (j==0) ids.push($(this).parent().attr('id').substr(2)); // i_
        });
    }
    data.push(ids);
    // additional checkups if the data we collected makes sense (note length-1)
    for (var j=0; j < data.length-1; j++){
        var c = remdublicates(data[j]);
        if (c.length == 1){
            notify('All values in a column are equal!');
            return false;
        }
    }
    return data;
}

function clean_plots(){
    $.each(_tilde.plots, function(n, i){
        $('#databrowser td[rel='+i+'], #databrowser th[rel='+i+']').removeClass('shared');
        $('#databrowser th[rel='+i+']').children('input').prop('checked', false);
    });
    _tilde.plots = [];
}
/**
*
*
* ============================================================================================================================================================================================================
*
*/
// RESPONSE FUNCTIONS
function resp__login(req, data){

    if (_tilde.last_request){ // something was not completed in a production mode
        var action = _tilde.last_request.split( _tilde.wsock_delim );
        __send(action[0], action[1], true);
    }
    data = JSON.parse(data);

    if (data.debug_regime){
        _tilde.debug_regime = true;
        $('#settings_debug').prop('checked', true);
    } else $('#settings_debug').prop('checked', false);

    if (_tilde.debug_regime) logger("RECEIVED SETTINGS: " + JSON.stringify(data.settings));
    for (var attrname in data.settings){ _tilde.settings[attrname] = data.settings[attrname] }
    //if (_tilde.debug_regime) logger("FINAL SETTINGS: " + JSON.stringify(_tilde.settings));

    // general switches (and settings)
    $('#version').text(data.version);
    document.title = data.title;
    $('#settings_title').val(data.title);

    if (data.demo_regime){
        _tilde.demo_regime = true;
        $('.protected').hide();
        if (data.custom_about_link){
            $('#custom_about_link_trigger').show();
            _tilde.custom_about_link = data.custom_about_link;
        }
    }
    $('#settings_webport').val(data.settings.webport);

    // display DBs
    set_dbs();
    var dbs_str = '', btns = '';
    if (!_tilde.demo_regime) btns += '<div class="btn btn3 right db-delete-trigger">delete</div>';

    $.each(_tilde.settings.dbs, function(n, item){
        if (n == 0) dbs_str += '<div rel=' + item + ' class="ipane_db_field ipane_db_field_active"><span>' + item + '</span></div>';
        else dbs_str += '<div rel=' + item + ' class="ipane_db_field"><span>' + item + '</span>' + btns + '</div>';
    });

    // display DB type
    if (!_tilde.demo_regime){
        if (_tilde.settings.db.engine == 'sqlite') $('#settings_db_type_sqlite').prop('checked', true);
        else if (_tilde.settings.db.engine == 'postgresql') { $('#settings_db_type_postgres').prop('checked', true); $('#settings_postgres').show(); }
    }

    for (var attrname in data.settings.db){
        if (attrname == 'type') continue;
        $('#settings_postgres_'+attrname).val(data.settings.db[attrname]);
    }

    if (!_tilde.demo_regime) dbs_str += '<div class="btn clear" id="create-db-trigger" style="width:90px;margin:20px auto 0;">create new</div>'
    $('div[rel=dbs] div').html( dbs_str );

    // display columns settings (depend on server + client state)
    $('#maxcols').html(_tilde.maxcols);

    _tilde.settings.avcols.sort(function(a, b){
        if (a.sort < b.sort) return -1;
        else if (a.sort > b.sort) return 1;
        else return 0;
    });

    $.each(_tilde.settings.avcols, function(n, item){
        var checked_state = item.enabled ? ' checked=checked' : '';
        $.each(data.cats, function(i, n){
            if ($.inArray(item.cid, n.includes) != -1){
                n.contains.push( '<li><input type="checkbox" id="s_cb_'+item.cid+'"'+checked_state+'" value="'+item.cid+'" /><label for="s_cb_'+item.cid+'"> '+item.category.charAt(0).toUpperCase() + item.category.slice(1)+'</label></li>' );
            }
        });
    });
    var result_html = '';
    $.each(data.cats, function(i, n){
        result_html += '<div class="ipane_cols_holder"><span>' + n.category.charAt(0).toUpperCase() + n.category.slice(1) + '</span><ul>' + n.contains.join('') + '</ul></div>';
    });
    $('#settings_cols').empty().append( result_html );

    var colnum_str = '';
    $.each([50, 100, 500], function(n, item){
        var checked_state = '';
        if (_tilde.settings.colnum == item) checked_state = ' checked=checked';
        colnum_str += ' <input type="radio"'+checked_state+' name="s_rdclnm" id="s_rdclnm_'+n+'" value="'+item+'" /><label for="s_rdclnm_'+n+'"> '+item+'</label>';
    });
    $('#ipane-maxitems-holder').empty().append(colnum_str);
    _tilde.settings.objects_expand ? $('#settings_objects_expand').prop('checked', true) : $('#settings_objects_expand').prop('checked', false);

    // display units settings (depend on client state only)
    var units_str = '';
    $.each(_tilde.units, function(k, v){
        //units_str += k.charAt(0).toUpperCase() + k.slice(1)+':';
        units_str += _tilde.unit_capts[k]+':';
        $.each(v, function(kk, vv){
            var checked_state = '';
            if (_tilde.settings.units[k] == kk) checked_state = ' checked=checked';
            units_str += ' <input type="radio"'+checked_state+' name="'+k+'" id="s_rd_'+k+'_'+kk+'" value="'+kk+'" /><label for="s_rd_'+k+'_'+kk+'"> '+kk+'</label>';
        });
        units_str += '<br /><br /><br />';
    });
    $('#ipane-units-holder').empty().append( units_str );

    // display scan settings (depend on server state only)
    _tilde.settings.skip_unfinished ? $('#settings_skip_unfinished').prop('checked', true) : $('#settings_skip_unfinished').prop('checked', false);

    if (!!_tilde.settings.skip_if_path) {
        $('#settings_skip_if_path').prop('checked', true);
        $('#settings_skip_if_path_mask').val(_tilde.settings.skip_if_path);
    } else $('#settings_skip_if_path').prop('checked', false);

    $('#settings_local_path').val(_tilde.settings.local_dir);

    // display export settings
    if (data.settings.exportability) $('#export_rows_trigger').show();

    if (!document.location.hash) document.location.hash = '#' + _tilde.settings.dbs[0];
}

function resp__browse(req, data){
    // reset objects
    _tilde.rendered = {};
    _tilde.tab_buffer = [];
    _tilde.plots = [];
    _tilde.last_chkbox = null;

    switch_menus();

    // we send table data in raw html (not json due to performance issues) and therefore some silly workarounds are needed
    data = data.split('||||');
    if (data.length>1) $('#countbox').empty().append(data[1]).show();

    $('#databrowser').hide().empty().append(data[0]);

    if (!$('#databrowser > tbody > tr').length){
        $('#databrowser tbody').append('<tr><td colspan=100 class=center>No data &mdash; <span class="link add_trigger">let\'s add!</span></td></tr>');
    }
    // else $('#tagcloud_holder').show();

    $('td._e').each(function(){
        var val = parseFloat( $(this).text() );
        if (val) $(this).text( ( Math.round(val * _tilde.units.energy[ _tilde.settings.units.energy ] * Math.pow(10, 5))/Math.pow(10, 5) ).toFixed(5) );
    });
    $('td._g').each(function(){
        var val = parseFloat( $(this).text() );
        if (val) $(this).text( Math.round(val * _tilde.units.energy[ _tilde.settings.units.energy ] * Math.pow(10, 4))/Math.pow(10, 4) );
    });

    $('span.units-energy').text(_tilde.settings.units.energy);
    $('#databrowser').show();
    $('#initbox').hide();
    if ($('#databrowser td').length > 1) $('#databrowser').tablesorter({sortMultiSortKey:'ctrlKey'});

    // GRAPH CHECKBOXES
    // (UNFORTUNATELY HERE : TODO)
    $('input.sc').click(function(ev){
        ev.stopImmediatePropagation();
        var cat = $(this).parent().attr('rel');
        $('.shared').removeClass('shared');

        $('input.SHFT_cb').prop('checked', false);

        if ($(this).is(':checked')){
            _tilde.plots.push(cat);
            if (_tilde.plots.length > 2){
                var old = _tilde.plots.shift();
                $('#databrowser th[rel='+old+']').children('input').prop('checked', false);
            }
        } else {
            $(this).parent().removeClass('shared');
            var iold = _tilde.plots.indexOf(cat);
            _tilde.plots.splice(iold, 1);
        }

        $.each(_tilde.plots, function(n, i){
            $('#databrowser td[rel='+i+'], #databrowser th[rel='+i+']').addClass('shared');
        });

        if (_tilde.plots.length) switch_menus(2);
        else switch_menus();
    });

    // this is to account any data request by hash
    if (req.hashes) __send('tags', {tids: req.tids, switchto: 'browse'});
    else document.location.hash = '#' + _tilde.settings.dbs[0] + '/browse';
}

function resp__tags(req, data){
    data = JSON.parse(data);
    var tags_html = '';

    if (req.tids && req.tids.length){
        // UPDATE AVAILABLE TAGS

        $('#countbox').hide();
        $('#initbox').show();

        $('a.taglink').removeClass('visibletag').hide(); // reset shown tags
        $('div.tagrow').hide();

        $.each(data, function(n, i){
            $('a._tag'+i).addClass('visibletag').show();
        });
        $.each(req.tids, function(n, i){
            $('a._tag'+i).addClass('visibletag activetag');
        });
        $('div.tagarea').each(function(){
            if ( $(this).find('a').filter( function(index){ return $(this).hasClass('visibletag') == true } ).length ){
                $(this).parent().show();
                $(this).children('div').show();
            }
        });
    } else {
        // BUILD TAGS FROM SCRATCH

        $.each(data.blocks, function(num, value){
            tags_html += '<div class="tagrow" rel="' + value.cid + '"><div class=tagcapt>' + value.category.charAt(0).toUpperCase() + value.category.slice(1) + ':</div><div class="tagarea">';

            value.content.sort(function(a, b){
                if (a.topic < b.topic) return -1;
                else if (a.topic > b.topic) return 1;
                else return 0;
            });
            $.each(value.content, function(n, i){
                tags_html += '<a class="taglink visibletag _tag' + i.tid + '" rel="' + i.tid + '" href=#>' + i.topic + '</a>';
            });
            tags_html += '</div></div>'
        });

        var empty_flag = false;
        if (!tags_html.length) empty_flag = true;

        $('#splashscreen').empty().append(tags_html);

        // TODO
        $('#splashscreen > div').each(function(){
            var content = $(this);
            $.each(data.cats, function(i, n){
                if ($.inArray(parseInt(content.attr('rel')), n.includes) != -1){
                    n.contains.push('<div class=tagrow>' + content.html() + '</div>');
                }
            });
        });
        var result_html = '';
        $.each(data.cats, function(i, n){
            result_html += '<div class=supercat> <div class=supercat_name>'+n.category.charAt(0).toUpperCase() + n.category.slice(1)+' (<span class="link">show</span>)</div> <div class=supercat_content>' + n.contains.join('') + '</div> </div>';
        });

        if (empty_flag) result_html = '<center>DB is empty!</center>';

        $('#splashscreen').empty().append(result_html);

        if (!$('#splashscreen_holder > #splashscreen').length) $('#splashscreen_holder').append($('#splashscreen'));

        $('div.tagrow').show();
    }

    if (!$.isEmptyObject(data)) $('#splashscreen').show();
    $('#splashscreen_holder').show();
    add_tag_expanders();
    // junction
    if (req.switchto) document.location.hash = '#' + _tilde.settings.dbs[0] + '/' + req.switchto;
}

function resp__list(obj, data){
    $('#connectors').show();
    open_ipane('conn-local');
    if (data.length)
        data = "<li>(<span rel='"+obj.path+"' class='link mult_read'>scan folder</span><span class=comma>, </span><span rel='"+obj.path+"' class='link mult_read' rev='recv'>scan folder + subfolders</span>)</li>"+data;
    data = "<ul class=jqueryFileTree style=display:none>" + data + "</ul>";

    if (obj.path == _tilde.filetree.root){
        $('#tilde_'+obj.transport+'_filetree').find('.start').remove();
        $('#tilde_'+obj.transport+'_filetree').append(data).find('ul:hidden').show();
        bindTree($('#tilde_'+obj.transport+'_filetree'), obj.transport);
        $('#settings_local_path').val(_tilde.settings.local_dir + obj.path);
    } else {
        var $el = $('#tilde_'+obj.transport+'_filetree a[rel="'+obj.path+'"]').parent();
        $el.removeClass('collapsed wait').addClass('expanded').append(data).find('ul:hidden').show();
        bindTree($el, obj.transport);
        $('#settings_local_path').val(_tilde.settings.local_dir + obj.path + _tilde.settings.local_dir.substr(_tilde.settings.local_dir.length-1));
    }
    _tilde.filetree.transports[obj.transport] = true;
}

function resp__report(obj, data){
    if (obj.directory){
        if (!data.length){
            // NO RESULTS
            $('span[rel="__read__'+obj.path+'"]').after('no files to scan in this folder').remove();

            _tilde.freeze = false; $('#loadbox').hide();
            _tilde.multireceive = 0;

            setTimeout(function(){ set_console(false) }, 1000);
            return;
        } else if (parseInt(data) == 1){
            // KEEP-ALIVE RESULTS
            logger('..', true);
            return;
        }
        _tilde.multireceive++;
        data = JSON.parse(data);
        if (!_tilde.multireceive) logger( '===========BEGIN OF SCAN '+obj.path+'===========', false, true );

        if (data.checksum) _tilde.hashes.push( data.checksum );
        if (data.error) logger( data.filename + ': ' + data.error );
        else logger( '<strong>' + data.filename + ': OK</strong>' );

        if (data.finished){
            // GOT RESULTS
            _tilde.freeze = false; $('#loadbox').hide();
            _tilde.multireceive = 0;

            var $el = $('#tilde_'+obj.transport+'_filetree span[rel="__read__'+obj.path+'"]');
            if (_tilde.hashes.length){
                $el.parent().children().show();
                $el.after('<span class="scan_done_trigger link">done</span>, <span class="scan_details_trigger link">details in console</span>').remove();
                //$el.after('<span dest="browse/' + tk + '" class="link">view reports</span>').remove();
                __send('browse', {hashes: _tilde.hashes});
                _tilde.hashes = [];
                $('#tagcloud_trigger').show();
                $('#noclass_trigger').show();
            } else $('span[rel="__read__'+obj.path+'"]').parent().html('(all files were omitted)');

            logger( '===========END OF SCAN '+obj.path+'===========' );

            setTimeout(function(){ set_console(false) }, 1000);
        }
    } else {
        _tilde.freeze = false; $('#loadbox').hide();
        __send('browse', {hashes: [ data ]});
        var $el = $('#tilde_'+obj.transport+'_filetree a[rel="'+obj.path+'"]');
        $el.addClass('_done').after('&nbsp; &mdash; <span class="scan_done_trigger link">done</span>');
    }
}

function resp__phonons(req, data){
    data = JSON.parse(data);
    if (!data) { notify('No phonon information found!'); return; }
    var result = '';
    $.each(data, function(i, v){
        for (var j=0; j<v.freqs.length; j++){
            var bz_info_header = '<span class=hdn>'+v.bzpoint+'</span>';
            var hide_class = '';
            var raman_place = '';
            var ir_place = '';
            var irrep_symb = v.irreps[j];
            if (j>0){ if (v.freqs[j-1] == v.freqs[j] && v.irreps[j-1] == v.irreps[j]){
                hide_class = ' class="phonons_dgnd hdn"'; irrep_symb = '<span class=hdn>'+v.irreps[j]+'</span>';
            }}
            if (j==0) bz_info_header = v.bzpoint;
            if (v.bzpoint == '0 0 0' && !!v.raman_active && !!v.ir_active){
                raman_place = (v.raman_active[j] == 'A') ? 'yes' : 'no';
                ir_place = (v.ir_active[j] == 'A') ? 'yes' : 'no';
            }
            eigv = v.ph_eigvecs[j];
            result += '<tr'+hide_class+'><td class="white bzp">' + bz_info_header + '</td><td class=white>' + irrep_symb + '</td><td class="white ph_ctrl _p" rev="'+eigv+'">' + Math.round( v.freqs[j] ) + '</td><td class=white>' + raman_place + '</td><td class=white>' + ir_place + '</td></tr>';
        }
    });
    $('#o_'+req.datahash+' div.ipane[rel=vib]').removeClass('loading');
    $('#o_'+req.datahash+' table.freqs_holder > tbody').empty().append( result );
    //if ($('th.thsorter').hasClass('header')) $('#freqs_holder').trigger("update");
    //else $('#freqs_holder').tablesorter({textExtraction:'complex',headers:{0:{sorter:'text'},1:{sorter:'text'},2:{sorter:'integer'},3:{sorter:'text'},4:{sorter:'text'}}});
    var rnd_ph = 0;
    if (_tilde.settings.units.phonons == 'THz') rnd_ph = 2;
    $('#o_'+req.datahash+' td._p').each(function(){
        $(this).text( Math.round( parseFloat($(this).text()) * _tilde.units.phonons[ _tilde.settings.units.phonons ] * Math.pow(10, rnd_ph) )/Math.pow(10, rnd_ph) );
    });
    $('span.units-phonons').html(_tilde.settings.units.phonons);
}

function resp__summary(req, data){
    data = JSON.parse(data);
    var info = JSON.parse(data.info);

    // PHONONS IPANES
    if (data.phonons && !_tilde.degradation){
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=vib]').show();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_dos]').show();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_bands]').show();
    } else {
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=vib]').hide();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_dos]').hide();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_bands]').hide();
    }

    // INPUT IPANE
    if (info.input){
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=inp]').show();
        if (info.prog.indexOf('Exciting') !== -1) info.input = info.input.replace(/&/g, '&amp;').replace(/</g, '&lt;');
        $('#o_'+req.datahash + ' div[rel=inp]').append('<div class=preformatter style="white-space:pre;height:489px;width:'+(_tilde.cwidth/2-65)+'px;margin:20px auto auto 20px;">'+info.input+'</div>');
    }

    // OPTGEOM IPANE
    if ($.inArray('geometry optimization', info.calctypes) != -1 && !_tilde.degradation){  $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=optstory]').show() }

    // ESTORY IPANE
    if (info.convergence.length && !_tilde.degradation) $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=estory]').show();

    // EDOS IPANE
    if (data.electrons.dos && !_tilde.degradation) $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_dos]').show();
    else $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_dos]').hide();

    // EBANDS IPANE
    if (data.electrons.bands && !_tilde.degradation) $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_bands]').show();
    else $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_bands]').hide();

    // SUMMARY (MAIN) IPANE
    var html = '<div><strong>'+info.location+'</strong></div>';
    html += '<div class=preformatter style="height:445px;"><ul class=tags>';
    if (info.warns){
        for (var i=0; i<info.warns.length; i++){
            html += '<li class=warn>'+info.warns[i]+'</li>';
        }
    }
    $.each(data.summary, function(num, value){
        if ($.inArray(value.content[0], ['&mdash;', '?']) == -1) {
            html += '<li><strong>' + value.category + '</strong>: <span>' + value.content.join('</span>, <span>') + '</span></li>';
        }
    });
    html += '</ul></div>';
    $('#o_'+req.datahash + ' div[rel=summary]').append('<div class=summary>'+html+'</div>');
    $('span._e').each(function(){
        var val = parseFloat( $(this).text() );
        if (val) $(this).text( ( Math.round(val * _tilde.units.energy[ _tilde.settings.units.energy ] * Math.pow(10, 5))/Math.pow(10, 5) ).toFixed(5) );
    });
    $('span._g').each(function(){
        var val = parseFloat( $(this).text() );
        if (val) $(this).text( Math.round(val * _tilde.units.energy[ _tilde.settings.units.energy ] * Math.pow(10, 4))/Math.pow(10, 4) );
    });
    $('span.units-energy').text(_tilde.settings.units.energy);

    // 3D IPANE
    open_ipane('3dview', req.datahash);
    if (!_tilde.degradation){
        _tilde.rendered[req.datahash] = true;
        $('#o_'+req.datahash + ' div.renderer').empty().append('<iframe id=f_'+req.datahash+' frameborder=0 scrolling="no" width="100%" height="500" src="/static/player.html?2#' + _tilde.settings.dbs[0] + '/' + req.datahash + '"></iframe>');
        //$('#phonons_animate').text('animate');
    } else {
        $('#o_'+req.datahash+' div.ipane[rel=3dview]').removeClass('loading').append('<br /><br /><p class=warn>Bumper! This content is not supported in your browser.<br /><br />Please, use a newer version of Chrome, Firefox, Safari or Opera browser.<br /><br />Thank you in advance and sorry for inconvenience.</p><br /><br />');
    }
}

function resp__settings(req, data){
    if (req.area == 'path'){
        _tilde.settings.local_dir = data;
        $('#tilde_local_filepath input').val(_tilde.settings.local_dir);
        $("#tilde_local_filetree").html('<ul class="jqueryFileTree start"><li class="wait">' + _tilde.filetree.load_msg + '</li></ul>');
        __send('list', {path:_tilde.filetree.root, transport:'local'} );
        $('#profile_holder').hide();
    } else if (req.area == 'cols'){
        // re-draw data table without modifying tags
        if (!_tilde.last_browse_request) return;
        if (!$('#databrowser').is(':visible')) return;
        __send('browse', _tilde.last_browse_request, true);
    } else if (req.area == 'switching'){
        //$('div.ipane_db_field_active').append('<div class="btn right db-make-active-trigger">make active</div>');
        if (!_tilde.demo_regime) $('div.ipane_db_field_active').append('<div class="btn btn3 right db-delete-trigger">delete</div>');
        $('div.ipane_db_field_active').removeClass('ipane_db_field_active');
        $('div[rel="' + req.switching + '"]').addClass('ipane_db_field_active').children('div').remove();
        _tilde.settings.dbs.splice(_tilde.settings.dbs.indexOf(req.switching), 1)
        _tilde.settings.dbs.unshift(req.switching);
        set_dbs();
    } else if (req.area == 'general'){
        notify('Saving new settings and restarting...');
        __send('restart');
        logger('RESTART SIGNAL SENT');
        setInterval(function(){document.location.reload()}, 2000); // setTimeout doesn't work here, 2 sec are optimal
    }
    $.jStorage.set('tilde_settings', _tilde.settings);
    logger('SETTINGS SAVED!');
}

function resp__clean(req, data){
    $('div[rel="' + req.db + '"]').remove();
    _tilde.settings.dbs.splice(_tilde.settings.dbs.indexOf(req.db), 1);
    set_dbs();
    logger('DATABASE ' + req.db + ' REMOVED.');
}

function resp__db_create(req, data){
    req.newname += '.db'
    //$('div.ipane_db_field:last').after('<div class="ipane_db_field" rel="' + req.newname + '"><span>' + req.newname + '</span><div class="btn right db-make-active-trigger">make active</div><div class="btn btn3 right db-delete-trigger">delete</div></div>');
    $('div.ipane_db_field:last').after('<div class="ipane_db_field" rel="' + req.newname + '"><span>' + req.newname + '</span><div class="btn btn3 right db-delete-trigger">delete</div></div>');
    _tilde.settings.dbs.push(req.newname);
    set_dbs();
    logger('DATABASE ' + req.newname + ' CREATED.');
}

function resp__db_copy(req, data){
    $('#d_cb_all').prop('checked', false);
    $('input.SHFT_cb').prop('checked', false);
    $('#db_copy_select').val('0');
    $('#databrowser tr').removeClass('shared');
    switch_menus();
}

function resp__delete(req, data){
    $('#d_cb_all').prop('checked', false);
    $.each(req.hashes, function(n, i){
        $('#i_' + i).remove();
    });

    switch_menus();
    $('#splashscreen').empty();

    if ($('#databrowser tbody').is(':empty')){
        document.location.hash = '#' + _tilde.settings.dbs[0];
    }
    $('#databrowser').trigger('update');
}

function resp__check_export(req, data){
    iframe_download( 'export', req.db, req.id );
}

function resp__ph_dos(req, data){
    dos_plotter(req, data, 'ph_dos_holder', {x: 'Frequency, cm<sup>-1</sup>', y: 'DOS, states/cm<sup>-1</sup>'});
}

function resp__e_dos(req, data){
    dos_plotter(req, data, 'e_dos_holder', {x: 'E - E<sub>f</sub>, eV', y: 'DOS, states/eV'});
}

function resp__ph_bands(req, data){
    bands_plotter(req, data, 'ph_bands_holder', 'Frequency, cm<sup>-1</sup>');
}

function resp__e_bands(req, data){
    bands_plotter(req, data, 'e_bands_holder', 'E - E<sub>f</sub>, eV');
}

function resp__optstory(req, data){
    e_plotter(req, data, 'optstory_holder', '&Delta;E<sub>tot</sub>, eV');
    open_ipane('3dview', req.datahash);
}

function resp__estory(req, data){
    e_plotter(req, data, 'estory_holder', 'log(E<sub>i</sub>-E<sub>i+1</sub>), eV');
}

function resp__try_pgconn(req, data){
    // continue gracefully
    __send('settings',  {area: 'general', settings: _tilde.settings} );
}
/**
*
*
* ============================================================================================================================================================================================================
*
*/
// DOM loading and default actions
$(document).ready(function(){

    if (!window.JSON) return; // sorry, we live in 2014

    _tilde.cwidth = document.body.clientWidth;
    var centerables = ['notifybox', 'loadbox', 'countbox', 'connectors', 'column_plot_holder'];
    var centerize = function(){
        $.each(centerables, function(n, i){
            document.getElementById(i).style.left = _tilde.cwidth/2 - $('#'+i).width()/2 + 'px';
        });
    };
    centerize();
    if (navigator.appName == 'Microsoft Internet Explorer'){
        _tilde.degradation = true;
        notify('Microsoft Internet Explorer doesn\'t support display of some content. You may try other browser.<br />Thank you in advance and sorry for inconvenience.');
    }
    $('#notifybox').hide();

    // initialize client-side settings
    _tilde.settings = $.jStorage.get('tilde_settings', _tilde.default_settings);
    _tilde.maxcols = Math.round(_tilde.cwidth/160) || 2;
    if (_tilde.settings.cols.length > _tilde.maxcols) _tilde.settings.cols.splice(_tilde.maxcols-1, _tilde.settings.cols.length-_tilde.maxcols+1);
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    (_tilde.conn = function(){
        _tilde.socket = new SockJS('http://' + window.location.host  + '/duplex', null, ['websocket', 'xhr-polling']);

        _tilde.socket.onopen = function(){
            logger('CONNECTED.');
            $('#notifybox').hide();
            _tilde.freeze = false;
            _tilde.connattempts = 0;
            clearInterval(_tilde.cinterval);
            _tilde.cinterval = null;
            __send('login',  {settings: _tilde.settings} );
        }

        _tilde.socket.onmessage = function(a){
            var split = a.data.split( _tilde.wsock_delim );
            var response = {};
            response.act = split[0];
            response.req = split[1].length ? JSON.parse(split[1]) : {};
            response.error = split[2];
            response.data = split[3];
            if (_tilde.debug_regime) logger('RECEIVED: '+response.act);
            if (response.act != 'report' || response.req.directory < 1){ _tilde.freeze = false; $('#loadbox').hide(); } // global lock for multireceive
            if (response.error && response.error.length>1){
                notify('Diagnostic message:<br />'+response.error);
                return;
            }
            if (window['resp__' + response.act]) window['resp__' + response.act](response.req, response.data);
            else notify('Unhandled action received: ' + response.act);
        }

        _tilde.socket.onclose = function(data){
            _tilde.connattempts += 1;
            if (_tilde.connattempts > _tilde.maxconnattempts){
                clearInterval(_tilde.cinterval);
                notify('Connection to program core cannot be established due to the failed server or network restrictions. Sometimes <a href=javascript:window.location.reload()>refresh</a> may help.');
                return;
            }
            logger('CONNECTION WITH PROGRAM CORE HAS FAILED!');
            if (_tilde.debug_regime){
                notify('Program core does not respond. Please, try to <a href=javascript:document.location.reload()>restart</a>.');
            } else {
                if (!_tilde.cinterval) _tilde.cinterval = setInterval(function(){ _tilde.conn() }, 2000);
            }
        }
    })();
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // STATE FUNCTIONALITY GIVEN BY ANCHORS
    setInterval(function(){
    if (_tilde.cur_anchor != document.location.hash){
        _tilde.cur_anchor = document.location.hash;

        var anchors = _tilde.cur_anchor.substr(1).split('/');

        if (!anchors.length || !_tilde.settings.dbs) return;

        if (_tilde.freeze){ _tilde.cur_anchor = null; return; } // freeze and wait for server responce if any command is given

        switch_menus();

        // db changed?
        if (anchors[0] != _tilde.settings.dbs[0]){
            $('#splashscreen').empty();
            __send('settings',  {area: 'switching', switching: anchors[0]} );
        }
        $('div.pane').hide();
        $('#initbox').hide();

        if (anchors[1]){
            
            $('#connectors').hide();
            $('#splashscreen_holder').hide();
            $('#data_holder').show();
            $('#databrowser').show();
            $('#tagcloud_trigger').show();
            $('#noclass_trigger').show();

            if (anchors[1] == 'browse'){

                // TABLE SCREEN

                $('#closeobj_trigger').hide();
                if ($('#splashscreen').is(':empty')) document.location.hash = '#' + anchors[0];
                _tilde.sortdisable = false; // sorting switch
            } else {

                // HASH (+WINDOW) SCREEN

                var hashes = anchors[1].split('+');

                if ($('#databrowser').is(':empty')){
                    _tilde.timeout3 = setInterval(function(){
                        if (!_tilde.freeze){
                            __send('browse', {hashes: hashes} );
                            clearInterval(_tilde.timeout3);
                        }
                    }, 500);
                } else {
                    clean_plots();
                    $.each(hashes, function(n, i){
                        if (!_tilde.rendered[i] && i.length == 56) {
                            var target_cell = $('#i_'+i);
                            if (!target_cell.length) return false; // this is a crunch, in principle, a history dispatcher is needed : TODO
                            var obf = $('<tr class=obj_holder></tr>').append( $('<th colspan=20></th>').append( $('#object_factory').clone().removeAttr('id').attr('id', 'o_'+i) ) );
                            target_cell.after(obf);
                            __send('summary',  {datahash: i} )
                            open_ipane('summary', i);
                            _tilde.rendered[i] = true;
                            window.scrollBy(0, 60);
                        }
                    });
                }
                _tilde.sortdisable = true; // sorting switch
            }

        } else {

            // MAIN TAGS SCREEN

            $('#databrowser').hide();
            $('div.downscreen').hide();
            $('#countbox').hide();
            $('#tagcloud_trigger').hide();
            $('#closeobj_trigger').hide();
            $('#noclass_trigger').hide();

            if (!$('#splashscreen_holder > #splashscreen').length || $('#splashscreen_holder > #splashscreen').is(':empty')){
                _tilde.timeout2 = setInterval(function(){
                if (!_tilde.freeze){
                    __send('tags', {tids: false});
                    clearInterval(_tilde.timeout2);
                }
                }, 500);
            } else {
                $('#data_holder').show();
                $('#splashscreen_holder').show();
                if ($('a.activetag').length) $('#initbox').show();
                add_tag_expanders();
            }

            _tilde.rendered = {}; // reset objects
            _tilde.tab_buffer = [];
            $('tr.obj_holder').remove();
            $('#data_holder').show();
        }
    }
    }, 333);
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // FILETREE DIR PROCESSOR
    $(document.body).on('click', 'div.filetree span.mult_read', function(){
        var $el = $(this), rel = $el.attr("rel"), rev = $el.attr("rev");
        $el.parent().children('span').hide();
        $el.after('<span rel=__read__'+rel+'>scan in progress...</span>');
        $el.remove();
        if (rev) __send('report',  {path: rel, directory: 2, transport:'local'} );
        else     __send('report',  {path: rel, directory: 1, transport:'local'} );
        $('#tagcloud_holder').hide();
        set_console(true);
    });

    // REPORT DONE TRIGGER
    $(document.body).on('click', 'span.scan_done_trigger', function(){
        $('#connectors').hide();
    });
    $(document.body).on('click', 'span.scan_details_trigger', function(){
        $('#console_trigger').trigger('click');
    });
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // CLOSE OR REMOVE CONTEXT WINDOW
    $('div._close').click(function(){
        //if ($('#flash-upload').is(':visible')) $('#file_uploadify').uploadifyClearQueue();
        // recursive closer if find _closable class
        (function closer( id ){
            var step_up = id.parent();
            if (!step_up) return;
            if (step_up.hasClass('_closable')) step_up.hide();
            else closer( step_up );
        })( $(this) );
    });

    // DELETE OBJECT TAB
    $(document.body).on('click', 'div._destroy', function(){
        var id = $(this).parent().parent().parent().attr('id').substr(2);

        close_obj_tab(id);

        var anchors = document.location.hash.substr(1).split('/');
        if (anchors.length != 2){
            notify('Unexpected behaviour (ref #1), please, report this to the developers!');
            return;
        }
        var hashes = anchors[1].split('+');
        var i = $.inArray(id, hashes);
        hashes.splice(i, 1);
        if (!hashes.length) document.location.hash = '#' + _tilde.settings.dbs[0] + '/browse';
        else document.location.hash = '#' + _tilde.settings.dbs[0] + '/' + hashes.join('+');
    });
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // DATABROWSER TABLE
    $('#databrowser').on('click', 'td', function(){
        if ($(this).parent().attr('id')) var id = $(this).parent().attr('id').substr(2);
        else return;

        if (!_tilde.settings.objects_expand){
            $('#d_cb_' + id).trigger('click');
            return;
        }

        if (_tilde.rendered[id]) {
            // close tab
            close_obj_tab(id);

            var anchors = document.location.hash.substr(1).split('/');
            if (anchors.length != 2){
                notify('Unexpected behaviour (ref #2), please, report this to the developers!');
                return;
            }
            var hashes = anchors[1].split('+');
            var i = $.inArray(id, hashes);
            hashes.splice(i, 1);
            if (!hashes.length) document.location.hash = '#' + _tilde.settings.dbs[0] + '/browse';
            else document.location.hash = '#' + _tilde.settings.dbs[0] + '/' + hashes.join('+');
        } else {
            // open tab
            var size = 0, key;
            for (key in _tilde.rendered){
                if (_tilde.rendered[key]) size++;
            }
            if (size == 3){
                // remove the first tab
                var anchors = document.location.hash.substr(1).split('/');
                if (anchors.length != 2){
                    notify('Unexpected behaviour (ref #3), please, report this to the developers!');
                    return;
                }
                var hashes = anchors[1].split('+');
                var first = hashes.splice(0, 1);

                close_obj_tab(first);

                document.location.hash = '#' + _tilde.settings.dbs[0] + '/' + hashes.join('+');
            }
            if (document.location.hash.length > 55){
                document.location.hash += '+' + id
            } else document.location.hash = '#' + _tilde.settings.dbs[0] + '/' + id;
            $('#closeobj_trigger').show();
        }
        $('div.downscreen').hide();
    });

    // DATABROWSER CHECKBOXES
    $('#databrowser').on('click', 'input.SHFT_cb', function(event){
        event.stopPropagation();
        if (_tilde.plots.length) clean_plots();

        if ($(this).is(':checked')) $(this).parent().parent().addClass('shared');
        else $(this).parent().parent().removeClass('shared');

        if (event.shiftKey && _tilde.last_chkbox){
            var $chkboxes = $('input.SHFT_cb');
            var start = $chkboxes.index(this);
            var end = $chkboxes.index(_tilde.last_chkbox);
            $chkboxes.slice(Math.min(start,end) + 1, Math.max(start,end)).trigger('click');
        }

        _tilde.last_chkbox = this;

        var flag = ($('input.SHFT_cb').is(':checked')) ? 1 : false;
        switch_menus(flag);
    });
    $('#databrowser').on('click', '#d_cb_all', function(){
        if (_tilde.plots.length) clean_plots();

        if ($(this).is(':checked') && $('#databrowser td').length > 1) {
            $('input.SHFT_cb').prop('checked', true);
            $('#databrowser tr').addClass('shared');
            switch_menus(1);
        } else {
            $('input.SHFT_cb').prop('checked', false);
            $('#databrowser tr').removeClass('shared');
            switch_menus();
        }
    });

    // IPANE COMMANDS
    $(document.body).on('click', 'ul.ipane_ctrl li', function(){
        var cmd = $(this).attr('rel');
        if (_tilde.freeze && !_tilde.tab_buffer[cmd] && cmd != 'admin'){ notify(_tilde.busy_msg); return; }
        var target = $(this).parents('.object_factory_holder');
        target = (target.length) ? target.attr('id').substr(2) : false;
        open_ipane(cmd, target);
    });

    // PHONONS TABLE
    //$('th.thsorter').click(function(){
    //    $('td.white span').removeClass('hdn');
    //});
    $('#databrowser').on('click', 'div.ph_degenerated_trigger', function(){
        var target = $(this).parents('.object_factory_holder').attr('id').substr(2);
        var capt = $(this).text();
        if (capt.indexOf('show') != -1){
            $('#o_'+target+' tr.phonons_dgnd').removeClass('hdn');
            $(this).text( capt.replace('show', 'hide') );
        } else {
            $('#o_'+target+' tr.phonons_dgnd').addClass('hdn');
            $(this).text( capt.replace('hide', 'show') );
        }
    });
    $('#databrowser').on('click', 'div.ph_animate_trigger', function(){
        if (_tilde.freeze){ notify(_tilde.busy_msg); return; }
        var target = $(this).parents('.object_factory_holder').attr('id').substr(2);
        var capt = $(this).text();
        if (capt.indexOf('stop') != -1){
            redraw_vib_links( false, target );
            document.getElementById('f_'+target).contentWindow.vibrate_3D( false );
            $(this).text( 'animate' );
        } else {
            open_ipane('3dview', target);
            redraw_vib_links( true, target );
            var phonons = '[' + $('#o_'+target+' td.ph_ctrl:first').attr('rev') + ']';
            document.getElementById('f_'+target).contentWindow.vibrate_3D( phonons );
            $('#o_'+target+' td.ph_ctrl span:first').addClass('red');
            $(this).html( '&nbsp;stop&nbsp;' );
        }
    });
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // DATABROWSER MENU
    $(document.body).on('click', '#add_trigger, span.add_trigger', function(){
        $('div.downscreen').hide();
        $('html, body').animate({scrollTop: 0});
        $('#connectors').show();
        open_ipane('conn-local');
        if (!_tilde.filetree.transports['local']){
            $("#tilde_local_filetree").html('<ul class="jqueryFileTree start"><li class="wait">' + _tilde.filetree.load_msg + '</li></ul>');
            __send('list',   {path:_tilde.filetree.root, transport:'local'} );
        }
    });
    $('#noclass_trigger').click(function(){
        $('#tagcloud_trigger').hide();
        $(this).hide();
        $('#splashscreen').empty();
        document.location.hash = '#' + _tilde.settings.dbs[0];
    });
    $('#closeobj_trigger').click(function(){
        $(this).hide();
        var anchors = document.location.hash.substr(1).split('/');
        if (anchors.length != 2){
            notify('Unexpected behaviour (ref #4), please, report this to the developers!');
            return;
        }
        var hashes = anchors[1].split('+');
        $.each(hashes, function(n, i){
            close_obj_tab(i);
        });
        document.location.hash = '#' + _tilde.settings.dbs[0] + '/browse';
    });
    $('#tagcloud_trigger').click(function(){
        set_console(false);
        if ($('#tagcloud_holder').is(':visible')){
            $('#tagcloud_holder').animate({ height: 'hide' }, { duration: 250, queue: false });
            $('#splashscreen_holder').append($('#splashscreen'));
        } else {
            $('#tagcloud_holder').animate({ height: 'show' }, { duration: 250, queue: false });
            $('#tagcloud_holder').append($('#splashscreen'));
        }
    });

    // CANCEL CONTEXT MENU
    $('#cancel_rows_trigger').click(function(){
        $('input.SHFT_cb, #d_cb_all').prop('checked', false);
        $('#databrowser tr').removeClass('shared');
        switch_menus();
    });
    $('#cancel_cols_trigger').click(function(){
        clean_plots();
        switch_menus();
    });

    // COPYING BETWEEN DATABASES
    $('#db_copy_select').change(function(){
        var tocopy = [], val = $(this).val();
        if (val==='0') return;
        $('input.SHFT_cb').each(function(){
            if ($(this).is(':checked')){
                tocopy.push( $(this).attr('id').substr(5) ); // d_cb_
            }
        });
        __send('db_copy',   {tocopy: tocopy, dest: val});
    });

    // EXPORT DATA FUNCTIONALITY
    $('#export_rows_trigger').click(function(){
        if ($('#databrowser tr.shared').length == 1){
            var id = $('#databrowser tr.shared').attr('id').substr(2);
            __send('check_export', {id: id, db: _tilde.settings.dbs[0]});
        } else notify('Batch export is not implemented.');
    });
    $('#export_cols_trigger').click(function(){
        if (!_tilde.plots.length) return;
        var data = gather_plots_data(), dump = '';
        if (!data) return;

        var ref = window.open('', 'export' + Math.floor(Math.random()*100));
        for (var j=0; j < data[0].length; j++){
            for (var i=0; i < data.length-1; i++){ // skip ids!
                dump += data[i][j] + '\t';
            }
            dump += '\n';
        }
        ref.document.body.innerHTML = '<pre>' + dump + '</pre>';
    });

    // PLOT COLUMNS (ONLY TWO AT THE TIME)
    $('#plot_trigger').click(function(){
        if (_tilde.plots.length == 1){ notify('Please, select yet another column to plot!'); return; }

        var plot = [{'color': '#0066CC', 'data': [], 'ids': []}], data = gather_plots_data(); // note ids!
        if (!data) return;

        for (var j=0; j < data[0].length; j++){
            var row = [];
            for (var i=0; i < data.length-1; i++){
                row.push(data[i][j]);
            }
            plot[0].data.push(row);
        }

        // this is to handle data clicks
        plot[0].ids = data[data.length-1];

        var options = {
            legend: {show: false},
            series: {lines: {show: false}, points: {show: true, fill: true, fillColor: '#0066CC'}, shadowSize: 3},
            xaxis: {labelHeight: 40},
            yaxis: {color: '#eeeeee', labelWidth: 50},
            grid: {borderWidth: 1, borderColor: '#000', hoverable: true, clickable: true}
        }
        var target = $('#column_plot');
        target.css('height', window.innerHeight*0.75 + 'px');

        $.plot(target, plot, options);
        $(target).unbind("plotclick").bind("plotclick", function(event, pos, item){
            if (item){
                var t = $('#d_cb_' + plot[0].ids[item.dataIndex]);
                $('html, body').animate({scrollTop: t.offset().top-100}, 1000);
                t.trigger('click');
            }
        });

        var x_label = $('#databrowser th[rel='+_tilde.plots[0]+']').children('span').html(), y_label = $('#databrowser th[rel='+_tilde.plots[1]+']').children('span').html(), h = target.height()/2+53; // rotate!
        target.append('<div style="position:absolute;z-index:499;width:300px;left:40%;bottom:0;text-align:center;font-size:1.25em;background:#fff;">'+x_label+'</div>&nbsp;');
        target.append('<div style="position:absolute;z-index:499;width:300px;left:0;top:'+h+'px;text-align:center;font-size:1.25em;transform:rotate(-90deg);transform-origin:left top;-webkit-transform:rotate(-90deg);-webkit-transform-origin:left top;-moz-transform:rotate(-90deg);-moz-transform-origin:left top;background:#fff;">'+y_label+'</div>');

        $('#column_plot_holder').show();
    });

    // DELETE ITEM
    $('#delete_trigger').click(function(){
        var todel = [];
        $('input.SHFT_cb').each(function(){
            if ($(this).is(':checked')){
                var i = $(this).attr('id').substr(5); // d_cb_
                todel.push( i );
                if (_tilde.rendered[i]){
                    // close tab
                    close_obj_tab(i);

                    var anchors = document.location.hash.substr(1).split('/');
                    if (anchors.length != 2){
                        notify('Unexpected behaviour (ref #5), please, report this to the developers!');
                        return;
                    }
                    var hashes = anchors[1].split('+');
                    var id = $.inArray(i, hashes);
                    hashes.splice(id, 1);
                    if (!hashes.length) document.location.hash = '#' + _tilde.settings.dbs[0] + '/browse';
                    else document.location.hash = '#' + _tilde.settings.dbs[0] + '/' + hashes.join('+');
                }
            }
        });
        __send('delete',   {hashes: todel});
    });

    // HIDE ITEM
    $('#hide_trigger').click(function(){
        $('div._closable').hide();
        if (!$.isEmptyObject(_tilde.rendered)){
            $('#closeobj_trigger').trigger('click');
        }

        $('input.SHFT_cb').each(function(){
            if ($(this).is(':checked')) $(this).parent().parent().remove();
        });

        switch_menus();
        if ($('#databrowser tbody').is(':empty')) $('#databrowser tbody').append('<tr><td colspan=100 class=center>No data to display!</td></tr>');
        $('#databrowser').trigger('update');
    });
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // TAGS SUPER-CATS
    $('#splashscreen').on('click', 'div.supercat', function(){
        var state = $(this).data('state') || 1;
        if (state == 1) $(this).children().children('span').html('hide').parent().next().show();
        else $(this).children().children('span').html('show').parent().next().hide();
        state++;
        if (state>2) state=1
        $(this).data('state', state);
    });

    // SPLASHSCREEN TAGCLOUD EXPANDERS
    $('#splashscreen').on('click', 'a.tagmore', function(){
        $(this).parent().removeClass('tagarea_reduced').prepend('<a class=tagless href=#>&uarr;</a>');
        $(this).remove();
        return false;
    });
    $('#splashscreen').on('click', 'a.tagless', function(){
        $(this).parent().addClass('tagarea_reduced').prepend('<a class=tagmore href=#>&rarr;</a>');
        $(this).remove();
        return false;
    });
    $('#splashscreen').on('click', 'div.tagarea, div.tagcapt', function(e){
        e.stopPropagation();
    });

    // SPLASHSCREEN TAG COMMANDS SINGLE CLICK
    $('#splashscreen').on('click', 'a.taglink', function(){
        var tags = gather_tags($('#splashscreen'), $(this));
        if (tags.length){
            __send('tags', {tids: tags});
        } else {
            $('#splashscreen a.taglink').removeClass('activetag').addClass('visibletag').show();
            $('#initbox').hide();
            add_tag_expanders();
        }
        return false;
    });

    // SPLASHSCREEN INIT TAG QUERY
    $('#init_trigger').click(function(){
        var tags = gather_tags($('#splashscreen'));
        __send('browse', {tids: tags});
        $('#initbox').hide();
    });
    $('#cnl_trigger').click(function(){
        $('#splashscreen a.taglink').removeClass('activetag').addClass('visibletag').show();
        $('#initbox').hide();
        add_tag_expanders();
    });
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // SETTINGS: GENERAL TRIGGERS
    $('#left_half_gear, #right_half_gear, #settings_trigger').click(function(){
        if ($('#profile_holder').is(':visible')){
            $('#profile_holder').hide();
        } else {
            $('#profile_holder').show();
            _tilde.demo_regime ? open_ipane('cols') : open_ipane('general');
        }
    });

    // SETTINGS: DATABASE MANAGEMENT
    $(document.body).on('click', '#metablock span, h1 span', function(){
        if ($('#profile_holder').is(':visible')){
            $('#profile_holder').hide();
        } else {
            $('#profile_holder').show();
            open_ipane('dbs');
        }
    });

    // SETTINGS: SWITCH DATABASES
    $(document.body).on('click', 'div.ipane_db_field', function(){
        if ($(this).attr('rel')) document.location.hash = '#' + $(this).attr('rel');
    });
    /*$(document).on('click', 'div.db-make-active-trigger', function(){
        var active_db = $(this).parent().attr('rel');
        __send('settings',  {area: 'switching', switching: active_db} );
    });*/

    // SETTINGS: DELETE DATABASE
    $(document.body).on('click', 'div.db-delete-trigger', function(ev){
        var $e = $(this);
        $e.html('confirm').removeClass('db-delete-trigger').addClass('db-delete-confirm-trigger');
        setTimeout(function(){ $e.html('delete').removeClass('db-delete-confirm-trigger').addClass('db-delete-trigger') }, 2000);
        ev.stopPropagation();
    });
    $(document.body).on('click', 'div.db-delete-confirm-trigger', function(ev){
        var db = $(this).parent().attr('rel');
        __send('clean',  {db: db} );
        ev.stopPropagation();
    });

    // SETTINGS: CREATE DATABASE
    $(document.body).on('click', '#create-db-trigger', function(){
        $(this).before('<div class="ipane_db_field"><form action="/" class="_hotkeyable"><input type="text" value="" id="create-db-name" maxlength="18" /><input type="submit" style="display:none" /></form><span>.db</span><div class="btn right _hotkey" id="create-db-confirm-trigger">create</div><div class="btn btn3 right" id="create-db-cancel-trigger">cancel</div></div>').hide();
        $('#create-db-name').focus();
        $('#create-db-confirm-trigger').click(function(){
            var newname = $('#create-db-name').val();
            $('#create-db-trigger').show();
            __send('db_create', {newname: newname});
            $(this).parent().remove();
        });
        $('#create-db-cancel-trigger').click(function(){ $(this).parent().remove(); $('#create-db-trigger').show(); });
    });

    // SETTINGS: MAXCOLS
    $('#settings_cols').on('click', 'input', function(){
        if ($('#settings_cols input:checked').length > _tilde.maxcols){
            $('#maxcols').parent().css('background-color', '#f99');
            return false;
        }
        $('#maxcols').parent().css('background-color', '#fff');
    });

    // SETTINGS: FILETREE PATH
    $('#filepath_apply_trigger').click(function(){
        __send('settings', { area: 'path', path: $('#settings_local_path').val() });
    });

    // SETTINGS: EXPLICIT CLICK TO SAVE
    $('div.settings-apply').click(function(){
        if ($('#settings_skip_unfinished').is(':visible')){

            // SETTINGS: SCAN
            _tilde.settings.skip_unfinished = $('#settings_skip_unfinished').is(':checked');
            _tilde.settings.skip_if_path = $('#settings_skip_if_path').is(':checked') ? $('#settings_skip_if_path_mask').val() : false;

            __send('settings',  {area: 'scan', settings: _tilde.settings} );
        } else if ($('#settings_cols').is(':visible')){

            // SETTINGS: COLS
            var sets = [];
            $('#settings_cols input').each(function(){
                if ($(this).is(':checked')) sets.push( parseInt( $(this).attr('value') ) );
            });
            if (!sets.length){
                notify('Please, choose at least anything to display.');
                return;
            }
            _tilde.settings.cols = sets;

            __send('settings', {area: 'cols', settings: _tilde.settings} );

            $('#profile_holder').hide();

        } else if ($('#ipane-maxitems-holder').is(':visible')){

            // SETTINGS: TABLE
            $('#ipane-maxitems-holder > input').each(function(){
                if ($(this).is(':checked')){
                    _tilde.settings.colnum = parseInt( $(this).attr('value') );
                }
            });

            // SETTINGS: EXPAND OBJECTS
            _tilde.settings.objects_expand = $('#settings_objects_expand').is(':checked');

            __send('settings', {area: 'cols', settings: _tilde.settings} );

            $('#profile_holder').hide();
        } else if ($('#ipane-units-holder').is(':visible')){
            $('#profile_holder').hide();

            // re-draw data table without modifying tags
            if (!_tilde.last_browse_request) return;
            if (!$('#databrowser').is(':visible')) return;
            __send('browse', _tilde.last_browse_request, true);
        } else if ($('#settings_title').is(':visible')){

            // TODO
            // here is some mess, whether the piece of settings is stored inside _tilde or inside _tilde.settings
            // we save here all inside _tilde.settings as it would be easier to process by a server
            _tilde.settings.title = $('#settings_title').val();
            _tilde.settings.debug_regime = $('#settings_debug').is(':checked');
            _tilde.settings.demo_regime = $('#settings_demo').is(':checked');
            _tilde.settings.webport = $('#settings_webport').val();

            if ($('#settings_db_type_sqlite').is(':checked')) _tilde.settings.db.engine = 'sqlite';
            else if ($('#settings_db_type_postgres').is(':checked')){
                _tilde.settings.db.engine = 'postgresql';
                _tilde.settings.db.host = $('#settings_postgres_host').val();
                _tilde.settings.db.user = $('#settings_postgres_user').val();
                _tilde.settings.db.port = $('#settings_postgres_port').val();
                _tilde.settings.db.password = $('#settings_postgres_password').val();
                _tilde.settings.db.dbname = $('#settings_postgres_dbname').val();
                __send('try_pgconn', {creds: _tilde.settings.db});
                return;
            }

            // SETTINGS: GENERAL
            __send('settings',  {area: 'general', settings: _tilde.settings} );
        }
    });

    // UNIVERSAL ENTER HOTKEY: NOTE ACTION BUTTON *UNDER THE SAME DIV* WITH THE FORM
    $(document.body).on('submit', 'form._hotkeyable', function(){
        $(this).parent().children('div._hotkey').trigger("click");
        return false;
    });

    // SETTINGS: UNITS
    $('#ipane-units-holder').on('click', 'input', function(){
        var sets = _tilde.settings.units;
        $('#ipane-units-holder > input').each(function(){
            if ($(this).is(':checked')){
                var name = $(this).attr('name');
                var value = $(this).attr('value');
                sets[ name ] = value;
            }
        });
        _tilde.settings.units = sets;
        $.jStorage.set('tilde_settings', _tilde.settings);
    });

    // SETTINGS: GENERAL
    $('#settings_db_type_postgres').click(function(){ $('#settings_postgres').show() });
    $('#settings_db_type_sqlite').click(function(){ $('#settings_postgres').hide() });

    // SETTINGS: RESTART + TERMINATE
    $('#core-restart').click(function(){
        if (_tilde.freeze){ notify(_tilde.busy_msg); return; }
        __send('restart');
        logger('RESTART SIGNAL SENT');
        setInterval(function(){document.location.reload()}, 2000); // setTimeout doesn't work here, 2 sec are optimal
    });
    $('#core-terminate').click(function(){
        if (_tilde.freeze){ notify(_tilde.busy_msg); return; }
        __send('terminate');
        logger('TERMINATE SIGNAL SENT');
        notify('This window may be closed now.');
    });
    $('#ui-restart').click(function(){ document.location.reload() });

    // ABOUT
    $('#about_trigger').click(function(){
        if (_tilde.custom_about_link) document.location = _tilde.custom_about_link;
        else document.location.hash = '#about';
    });
    $('#custom_about_link_trigger').click(function(){
        document.location = _tilde.custom_about_link;
    });
/**
*
*
* ============================================================================================================================================================================================================
*
*/
    // DEBUG CONSOLE
    $('#console_trigger').click(function(){
        set_console(true);
    });

    // ABOUT WINDOW
    $('#continue_trigger').click(function(){
        var action = function(){ document.location.hash = '#' + _tilde.settings.dbs[0]; }
        $("#tilde_logo").animate({ marginTop: '175px' }, { duration: 330, queue: false });
        $("#mainframe").animate({ height: 'hide' }, { duration: 330, queue: false, complete: function(){ action() } });
    });

    // RESIZE
    $(window).resize(function(){
        if (Math.abs(_tilde.cwidth - document.body.clientWidth) < 30) return; // width of scrollbar
        _tilde.cwidth = document.body.clientWidth;
        centerize();
        add_tag_expanders();
        _tilde.maxcols = Math.round(_tilde.cwidth/160) || 2;
        $('#maxcols').html(_tilde.maxcols);
    });

    // Q/q/ESC HOTKEYS TO CLOSE ALL (ESC KEY NOT WORKING IN FF)
    $(document).keyup(function(ev){
        if (ev.keyCode == 27 || ev.keyCode == 81 || ev.keyCode == 113){
            $('div._closable').hide();
            if (!$.isEmptyObject(_tilde.rendered)){
                $('#closeobj_trigger').trigger('click'); // TODO : FIXME
            }
        }
        return false;
    });
});
