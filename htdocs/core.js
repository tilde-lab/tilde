/**
*
* Tilde project: client core
* v290613
*
*/
// common flags, settings and object for their storage
var _tilde = {};
_tilde.debug = false; // major debugging switch
_tilde.protected = false;
_tilde.degradation = false;
_tilde.hashes = [];
_tilde.rendered = {}; // datahash:structure, ... ,
_tilde.tab_buffer = [];
_tilde.last_request = false; // todo: request history dispatcher
_tilde.last_browse_request = false; // todo: request history dispatcher
_tilde.freeze = false;
_tilde.wsock_delim = '~#~#~';
_tilde.cur_anchor = false;
_tilde.multireceive = 0;
_tilde.scrollmemo = 0;
_tilde.filetree = {};
_tilde.filetree.transports = [];
_tilde.filetree.root = '';
_tilde.filetree.load_msg = 'Requesting directory listing...';
_tilde.busy_msg = 'Program core is now busy serving your request. Please, wait a bit and try again.';
_tilde.cw = 0;

// units
_tilde.units = {
    'energy': {'au':1, 'eV':27.2113834, 'Ry':13.6056991},
    'phonons': {'cm<sup>-1</sup>':1, 'THz':0.029979}
};
_tilde.unit_capts = {'energy':'Total electronic energy', 'phonons':'Phonon frequencies'};
_tilde.default_settings = {};
_tilde.default_settings.units = {'energy':'au', 'phonons':'cm<sup>-1</sup>'};
_tilde.default_settings.cols = [1, 1001, 1002, 1005, 1006, 6]; // these are cid's of hierarchy API (cid>1000 means specially defined column)
_tilde.default_settings.colnum = 75;

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
* ======================================================================================================
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
    if (_tilde.debug) logger('REQUESTED: '+act);
    if (_tilde.freeze){ notify(_tilde.busy_msg); return; }
    if (!nojson) req ? req = $.toJSON(req) : req = '';
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
function set_repos(){
    $('#metablock').html( '<span class="link white">' + _tilde.settings.dbs[0] + '</span>' );

    var title = 'Current repository: ' + _tilde.settings.dbs[0];
    if (!!_tilde.settings.dbs.length && _tilde.settings.dbs.length > 1) title += ' (<span class=link>' + (_tilde.settings.dbs.length - 1) + ' more</span>)';
    $('h1').html( title );

    var options = '<option value="0" selected="selected">copy to ...</option>';
    $.each(_tilde.settings.dbs, function(n, item){
        if (n==0) return true;
        options += '<option value="' + item + '">copy to ' + item + '</option>';
    });
    $('#db_copy_select').empty().append(options);
}
function set_user_settings( settings ){
    //if (_tilde.debug) logger("RECEIVED SETTINGS: " + $.toJSON(settings));

    for (var attrname in settings){ _tilde.settings[attrname] = settings[attrname] }
    //if (_tilde.debug) logger("ACTUAL SETTINGS: " + $.toJSON(_tilde.settings));

    // render databases
    //
    set_repos();
    var dbs_str = '', btns = '<div class="btn right db-make-active-trigger">make active</div>';
    if (!_tilde.protected) btns += '<div class="btn btn3 right db-delete-trigger">delete</div>';

    $.each(_tilde.settings.dbs, function(n, item){
        if (n == 0) dbs_str += '<div rel=' + item + ' class="ipane_db_field ipane_db_field_active"><span>' + item + '</span></div>';
        else dbs_str += '<div rel=' + item + ' class="ipane_db_field"><span>' + item + '</span>' + btns + '</div>';
    });

    if (!_tilde.protected) dbs_str += '<div class="btn clear" id="create-db-trigger" style="width:90px;margin:20px auto 0;">create new</div>'
    $('div[rel=dbs] div').html( dbs_str );

    // render columns settings (depend on server + client state)
    //
    $('#maxcols').html(_tilde.maxcols);
    $('#ipane_cols_holder > ul').empty();
    _tilde.settings.avcols.sort(function(a, b){
        if (a.order < b.order) return -1;
        else if (a.order > b.order) return 1;
        else return 0;
    });
    $.each(_tilde.settings.avcols, function(n, item){
        var checked_state = item.enabled ? ' checked=true' : '';
        $('#ipane_cols_holder > ul').append( '<li><input type="checkbox" id="s_cb_'+item.cid+'"'+checked_state+'" value="'+item.cid+'" /><label for="s_cb_'+item.cid+'"> '+item.category+'</label></li>' );
    });
    var colnum_str = '';
    $.each([50, 75, 100], function(n, item){
        var checked_state = '';
        if (_tilde.settings.colnum == item) checked_state = ' checked=true';
        colnum_str += ' <input type="radio"'+checked_state+' name="s_rdclnm" id="s_rdclnm_'+n+'" value="'+item+'" /><label for="s_rdclnm_'+n+'"> '+item+'</label>';
    });
    $('#ipane-maxitems-holder').empty().append(colnum_str);

    // render units settings (depend on client state only)
    //
    var units_str = '';
    $.each(_tilde.units, function(k, v){
        //units_str += k.charAt(0).toUpperCase() + k.slice(1)+':';
        units_str += _tilde.unit_capts[k]+':';
        $.each(v, function(kk, vv){
            var checked_state = '';
            if (_tilde.settings.units[k] == kk) checked_state = ' checked=true';
            units_str += ' <input type="radio"'+checked_state+' name="'+k+'" id="s_rd_'+k+'_'+kk+'" value="'+kk+'" /><label for="s_rd_'+k+'_'+kk+'"> '+kk+'</label>';
        });
        units_str += '<br /><br /><br />';
    });
    $('#ipane-units-holder').empty().append( units_str );

    // render scan settings (depend on server state only)
    //
    $('#settings_local_path').val(_tilde.settings.local_dir);
    _tilde.settings.quick_regime ? $('#settings_quick_regime').attr('checked', true) : $('#settings_quick_regime').attr('checked', false);
    _tilde.settings.skip_unfinished ? $('#settings_skip_unfinished').attr('checked', true) : $('#settings_skip_unfinished').attr('checked', false);

    if (!!_tilde.settings.skip_if_path) {
        $('#settings_skip_if_path').attr('checked', true);
        $('#settings_skip_if_path_mask').val(_tilde.settings.skip_if_path);
    } else $('#settings_skip_if_path').attr('checked', false);
    
    // render export settings
    //
    if (settings.exportability) $('#export_trigger').show();
}
function open_ipane(cmd, target){
    if (!!target) var current = $('#o_'+target+' ul.ipane_ctrl li[rel='+cmd+']');
    else var current = $('ul.ipane_ctrl li[rel='+cmd+']');
    if (!current.length) { notify('Error opening pane '+cmd+'!'); return; }

    current.parent().children('li').css('border-bottom-color', '#06c');
    current.css('border-bottom-color', '#fff').parent().parent().children( 'div.ipane' ).hide();
    current.parent().parent().find( 'div[rel='+cmd+']' ).show();

    if (!target){
        switch(cmd){
            case 'check_version':
                $('div[rel=check_version] div').empty();
                __send('check_version');
                break;
        }
        return; }
    if (_tilde.tab_buffer.indexOf(target+'_'+cmd) != -1) return;

    switch(cmd){
        case 'ph_dos':
        case 'e_dos':
        case 'ph_bands':
        case 'e_bands':
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
    if (delete _tilde.rendered[tab_id]) $('#i_'+tab_id).next('tr').remove();
    _tilde.tab_buffer = $.grep(_tilde.tab_buffer, function(val, index){
        if (val.indexOf(tab_id) == -1) return true;
    });
}
function iframe_download( request, scope, hash ){ // used by player
    $('body').append('<form style="display:none;" id="data-download-form" action="/' + request + '/' + scope + '/' + hash + '" target="file-process" method="get"></form>');
    $('#data-download-form').submit().remove();
}
function dos_plotter(req, plot, divclass, axes){
    var plot = $.evalJSON(plot);
    var options = {legend:{show:false}, series:{lines:{show:true}, points:{show:false}, shadowSize:0}, xaxis:{color:'#000', labelHeight:40}, yaxis:{ticks:[], labelWidth:30}, grid:{borderWidth:1, borderColor:'#000'}};

    var cpanel = $('#o_'+req.datahash+' div.'+divclass).prev('div');
    cpanel.parent().removeClass('ii');

    for (var i=0; i < plot.length; i++){
        cpanel.prepend('<input type="checkbox" name="' + plot[i].label + '" checked="checked" id="cb_' + req.datahash + '_' + plot[i].label + '" rev="' + $.toJSON(plot[i].data) + '" rel="'+plot[i].color+'" />&nbsp;<label for="cb_'+ req.datahash + '_' + plot[i].label +'" style="color:' + plot[i].color + '">' + plot[i].label + '</label>&nbsp;');
    }
    function plot_user_choice(){
        var data_to_plot = [];
        cpanel.find("input:checked").each(function(){
            var d = $(this).attr('rev');
            data_to_plot.push({color: $(this).attr('rel'), data: $.evalJSON( $(this).attr('rev') )});
        });
        var target = $('#o_'+req.datahash+' div.'+divclass);
        $.plot(target, data_to_plot, options);

        target.append('<div style="position:absolute;z-index:50;width:200px;left:40%;bottom:0;text-align:center;font-size:1.5em;background:#fff;">'+axes.x+'</div>  <div style="position:absolute;z-index:50;width:200px;left:0;top:300px;text-align:center;font-size:1.5em;-webkit-transform:rotate(-90deg);-webkit-transform-origin:left top;-moz-transform:rotate(-90deg);-moz-transform-origin:left top;background:#fff;">'+axes.y+'</div>');
    }
    cpanel.find("input").click(plot_user_choice);
    plot_user_choice();
    cpanel.children('div.export_plot').click(function(){ export_data(plot) });
}
function bands_plotter(req, plot, divclass, ordinate){
    var plot = $.evalJSON(plot);
    var options = {legend:{show:false}, series:{lines:{show:true}, points:{show:false}, shadowSize:0}, xaxis:{color:'#000', labelHeight:40, font:{size:9.5}, labelAngle:270}, yaxis:{color:'#000', labelWidth:50}, grid:{borderWidth:1, borderColor:'#000'}};

    var target = $('#o_'+req.datahash+' div.'+divclass);

    var cpanel = target.prev('div');
    cpanel.parent().removeClass('ii');

    options.xaxis.ticks = plot[0].ticks
    options.xaxis.ticks[options.xaxis.ticks.length-1][1] = '' // avoid cropping in canvas
    $.plot(target, plot, options);

    target.append('<div style="position:absolute;z-index:50;width:200px;left:0;top:300px;text-align:center;font-size:1.25em;-webkit-transform:rotate(-90deg);-webkit-transform-origin:left top;-moz-transform:rotate(-90deg);-moz-transform-origin:left top;background:#fff;">'+ordinate+'</div>');

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
    var max_width = $('div.tagarea:first').width()-40+1;
    $('#splashscreen div.tagarea_reduced').each(function(){
        var w = 0;
        $(this).find('a.taglink').filter(':visible').each(function(){
            w += $(this).width()+10; // margin + border + padding are hard-coded TODO
            if (w >= max_width) {
                $(this).before('<a class=tagmore href=#>&rarr;</a>');
                return false;
            }
        });
    });
}
function switch_menus(reverse){
    if (reverse) { $('div.menu_main_cmds').show(); $('div.menu_ctx_cmds').hide(); }
    else { $('div.menu_main_cmds').hide(); $('div.menu_ctx_cmds').show(); }
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
/**
*
*
* ======================================================================================================
*
*/
// PROCESS RESPONCE FUNCTIONS
function resp__login(req, data){
    data = $.evalJSON(data);

    // global switches
    $('#version').text( data.version );
    document.title = data.title;
    if (data.debug_regime) _tilde.debug = true;
    if (data.demo_regime){
        _tilde.protected = true;
        $('div.protected, li.protected').hide();
    }    

    // something was not completed in production mode
    if (_tilde.last_request){
        var action = _tilde.last_request.split( _tilde.wsock_delim );
        __send(action[0], action[1], true);
    }

    set_user_settings(data.settings);

    if (data.amount){
        logger('RECORDS IN DATABASE: ' + data.amount);
        // state restores here by anchors!
        if (!document.location.hash) document.location.hash = '#tags';
        $('#continue_trigger').removeAttr('rel');
    } else document.location.hash = '#start';
}
function resp__browse(req, data){
    // we send table data in raw html (not json due to performance issues) and therefore some silly workarounds are needed
    data = data.split('||||');
    if (data.length>1) $('#countbox').empty().append(data[1]).show();

    $('#databrowser').hide().empty().append(data[0]);

    if (!$('#databrowser > tbody > tr').length){
        $('#databrowser tbody').append('<tr><td colspan=100 class=center>No data &mdash; <span class="link add_trigger">let\'s add!</span></td></tr>');
    } else $('#tagcloud_holder').show();

    $('td._e').each(function(){
        var val = parseFloat( $(this).text() );
        if (val) $(this).text( ( Math.round(val * _tilde.units.energy[ _tilde.settings.units.energy ] * Math.pow(10, 5))/Math.pow(10, 5) ) );
    });

    $('span.units-energy').text(_tilde.settings.units.energy);
    $('#databrowser').show();
    if ($('#databrowser td').length > 1) $('#databrowser').tablesorter({sortMultiSortKey:'ctrlKey'});

    // this is to account:
    // (1) empty browse request in start_junction
    // (2) any data request by hash
    // (3) tagcloud queries
    if ($.isEmptyObject(req)) {
        document.location.hash = '#continue';
    } else {
        if (req.hashes) req = {tids: false, defer_load: true};
        if (req.defer_load) __send('tags', {tids: req.tids, render: 'tagcloud', switchto: 'browse'});
        else document.location.hash = '#browse';
    }
}
function resp__tags(req, data){
    data = $.evalJSON(data);
    var tags_html = '';

    if (req.tids && req.tids.length){
        if (req.render == 'splashscreen') $('#initbox').show();
        
        // splashscreen or tagcloud dynamic update
        $('a.taglink').removeClass('vi').hide(); // reset shown tags
        $('div.tagcol').hide();

        $.each(data, function(n, i){
            $('a.taglink[rel='+i+']').addClass('vi').show();
        });
        $.each(req.tids, function(n, i){
            $('a.taglink[rel='+i+']').addClass('vi activetag');
        });
        $('div.tagarea').each(function(){
            if ( $(this).find('a').filter( function(index){ return $(this).hasClass('vi') == true } ).length ){
                $(this).parent().show();
                $(this).children('div').show();
            }
        });
    } else {
        // both splashscreen and tagcloud dynamic re-drawn
        $.each(data, function(num, value){
            tags_html += '<div class=tagcol><div class=tagcapt>' + value.category.charAt(0).toUpperCase() + value.category.slice(1) + ':</div><div class="tagarea tagarea_reduced">';

            value.content.sort(function(a, b){
                if (a.topic < b.topic) return -1;
                else if (a.topic > b.topic) return 1;
                else return 0;
            });
            $.each(value.content, function(n, i){
                tags_html += '<a class="taglink vi" rel=' + i.tid + ' href=#>' + i.topic + '</a>';
            });
            tags_html += '</div></div>'
        });
        if (!tags_html.length) tags_html = '&nbsp;Repository is empty!';

        $('#splashscreen').empty().append(tags_html);
        $('#tagcloud').empty().append(tags_html);

        $('#tagcloud div.tagarea_reduced').removeClass('tagarea_reduced');
        $('div.tagcol').show();
    }

    // show requested place with tags: i.e. splashscreed or tagcloud
    if (!$.isEmptyObject(data)) {
        $('#splashscreen').show();
        $('#tagcloud').show();
    }

    if (req.render == 'splashscreen'){        
        $('#splashscreen_holder').show();
        add_tag_expanders();
    }

    // junction
    if (req.switchto) document.location.hash = '#' + req.switchto;
}
function resp__list(obj, data){
    if (data.substr(0, 20) == 'SETUP_NEEDED_TRIGGER'){ // bad design, fixme!!!
        //$('#connectors').hide();
        $('#profile_holder').show();
        open_ipane('scan');
        $('#settings_local_path').val( data.substr(20) ).focus();
        return;
    }
    if (data.length)
        data = "<li>(<span rel='"+obj.path+"' class='link mult_read'>scan folder</span><span class=comma>, </span><span rel='"+obj.path+"' class='link mult_read' rev='recv'>scan folder + subfolders</span>)</li>"+data;
    data = "<ul class=jqueryFileTree style=display:none>" + data + "</ul>";

    if (obj.path == _tilde.filetree.root){
        $('#tilda-'+obj.transport+'-filetree').find('.start').remove();
        $('#tilda-'+obj.transport+'-filetree').append(data).find('ul:hidden').show();
        bindTree($('#tilda-'+obj.transport+'-filetree'), obj.transport);
    } else {
        var $el = $('#tilda-'+obj.transport+'-filetree a[rel="'+obj.path+'"]').parent();
        $el.removeClass('collapsed wait').addClass('expanded').append(data).find('ul:hidden').show();
        bindTree($el, obj.transport);
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

            setTimeout(function(){
                $('#debug-holder').animate({ height: 'hide' }, { duration: 250, queue: false });
            }, 1000);
            return;
        } else if (parseInt(data) == 1){
            // KEEP-ALIVE RESULTS
            logger('..', true);
            return;
        }

        _tilde.multireceive++;
        data = $.evalJSON(data);
        if (!_tilde.multireceive) logger( '===========BEGIN OF SCAN '+obj.path+'===========', false, true );


        if (data.checksum) _tilde.hashes.push( data.checksum );
        if (data.error) logger( data.filename + ': ' + data.error );
        else logger( '<strong>' + data.filename + ': OK</strong>' );

        if (data.finished){
            // GOT RESULTS
            _tilde.freeze = false; $('#loadbox').hide();
            _tilde.multireceive = 0;

            var $el = $('#tilda-'+obj.transport+'-filetree span[rel="__read__'+obj.path+'"]');
            if (_tilde.hashes.length){
                $el.parent().children().show();
                $el.after('<span class="scan_done_trigger link">done</span>, <span class="scan_details_trigger link">details in console</span>').remove();
                //$el.after('<span dest="browse/' + tk + '" class="link">view reports</span>').remove();
                __send('browse', {hashes: _tilde.hashes});
                _tilde.hashes = [];
                $('#tagcloud_trigger').show();
                $('#noclass_trigger').show();
            } else $('span[rel="__read__'+obj.path+'"]').parent().html('(folder contains unsupported files)');

            logger( '===========END OF SCAN '+obj.path+'===========' );

            setTimeout(function(){
                $('#debug-holder').hide();
            }, 750);
        }
    } else {
        _tilde.freeze = false; $('#loadbox').hide();
        __send('browse', {hashes: [ data ]});
        var $el = $('#tilda-'+obj.transport+'-filetree a[rel="'+obj.path+'"]');
        $el.addClass('_done').after('&nbsp; &mdash; <span class="scan_done_trigger link">done</span>');
    }
}
function resp__phonons(req, data){
    data = $.evalJSON(data);
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
    $('#o_'+req.datahash+' div.ipane[rel=vib]').removeClass('ii');
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
function resp__make3d(req, data){
    _tilde.rendered[req.datahash] = data;
    $('#o_'+req.datahash + ' div.renderer').empty().append('<iframe id=f_'+req.datahash+' frameborder=0 scrolling="no" width="100%" height="500" src="/static/player.html#'+req.datahash+'"></iframe>');
    //$('#phonons_animate').text('animate');
}
function resp__summary(req, data){
    data = $.evalJSON(data);
    var info = $.evalJSON(data.info);
    if (data.phonons && !_tilde.degradation){
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=vib]').show();
        //$('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_dos]').show();
        //$('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_bands]').show();
    } else {
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=vib]').hide();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_dos]').hide();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=ph_bands]').hide();
    }

    if (data.electrons && !_tilde.degradation){
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_dos]').show();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_bands]').show();
    }
    /*if (!data.electrons && !_tilde.protected && info.prog.indexOf('CRYSTAL') != -1 && !_tilde.degradation){
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_dos]').show();
        $('#o_'+req.datahash+' ul.ipane_ctrl li[rel=e_bands]').show();
        var msg = '<div class="notice">Eigenvalues / eigenvectors are missing in CRYSTAL-only output.<br />Please, run PROPERTIES on the wavefunction file (fort.9) for the output:<div>'+info.location+'</div>using the following d3-input as a template:<div>NEWK<br><span>2 2</span><br>1 2<br>66 <span>4</span><br>67 <span>4</span><br>END<br></div>Then scan the folder with the obtained new output: if it corresponds to the current item, they would be merged and labeled CRYSTAL+PROPERTIES.</div>';
        $('#o_'+req.datahash+' div.e_bands-holder').prepend(msg);
        _tilde.tab_buffer.push(req.datahash+'_e_bands');
        $('#o_'+req.datahash+' div.ipane[rel=e_bands]').removeClass('ii');
        $('#o_'+req.datahash+' div.e_dos-holder').prepend(msg);
        _tilde.tab_buffer.push(req.datahash+'_e_dos');
        $('#o_'+req.datahash+' div.ipane[rel=e_dos]').removeClass('ii');
    }*/

    var html = '<div><strong>'+info.location+'</strong></div>';
    html += '<div style="height:410px;overflow-x:visible;overflow-y:scroll;"><ul class=tags>';
    $.each(data.tags, function(num, value){
        html += '<li><strong>' + value.category.charAt(0).toUpperCase() + value.category.slice(1) + '</strong>: <span>' + value.content.join('</span>, <span>') + '</span></li>';
    });
    if (info.warns){
        for (var i=0; i<info.warns.length; i++){
            html += '<li style="background:#f99;">'+info.warns[i]+'</li>';
        }
    }
    html += '</ul></div>';
    $('#o_'+req.datahash + ' div[rel=summary]').empty().append('<div class=summary>'+html+'</div>');
    open_ipane('3dview', req.datahash);
    if (!_tilde.degradation) __send('make3d',  {datahash: req.datahash} );
    else {
        $('#o_'+req.datahash+' div.ipane[rel=3dview]').removeClass('ii').append('<br /><br />Bumper! This content is not supported in your browser.<br /><br />Please, use a newer version of Chrome, Firefox, Safari or Opera browser.<br /><br />Thank you in advance and sorry for inconvenience.<br /><br />');
    }
}
function resp__settings(req, data){
    $.jStorage.set('tilde_settings', _tilde.settings);
    logger('SETTINGS SAVED!');
    if (req.area == 'scan'){
        $("#tilda-local-filetree").html('<ul class="jqueryFileTree start"><li class="wait">' + _tilde.filetree.load_msg + '</li></ul>');
        __send('list',   {path:_tilde.filetree.root, transport:'local'} );
        $('#profile_holder').hide();
    } else if (req.area == 'cols'){
        // re-draw data table without modifying tags
        if (!_tilde.last_browse_request) return;
        if (!$('#databrowser').is(':visible')) return;
        __send('browse', _tilde.last_browse_request, true);
    } else if (req.area == 'switching'){
        $('div.ipane_db_field_active').append('<div class="btn right db-make-active-trigger">make active</div>');
        if (!_tilde.protected) $('div.ipane_db_field_active').append('<div class="btn btn3 right db-delete-trigger">delete</div>');
        $('div.ipane_db_field_active').removeClass('ipane_db_field_active');
        $('div[rel="' + req.switching + '"]').addClass('ipane_db_field_active').children('div').remove();
        _tilde.settings.dbs.splice(_tilde.settings.dbs.indexOf(req.switching), 1)
        _tilde.settings.dbs.unshift(req.switching);
        set_repos();

        $('#splashscreen').empty();
        if (document.location.hash == 'tags' || document.location.hash == '#tags') __send('tags', {tids: false, render: 'splashscreen', switchto: false});
        else document.location.hash = '#tags';
        $('#splashscreen_holder').show();
    }
}
function resp__clean(req, data){
    $('div[rel="' + req.db + '"]').remove();
    _tilde.settings.dbs.splice(_tilde.settings.dbs.indexOf(req.db), 1);
    set_repos();
    logger('DATABASE ' + req.db + ' REMOVED.');
}
function resp__db_create(req, data){
    req.newname += '.db'
    $('div.ipane_db_field:last').after('<div class="ipane_db_field" rel="' + req.newname + '"><span>' + req.newname + '</span><div class="btn right db-make-active-trigger">make active</div><div class="btn btn3 right db-delete-trigger">delete</div></div>');
    _tilde.settings.dbs.push(req.newname);
    set_repos();
    logger('DATABASE ' + req.newname + ' CREATED.');
}
function resp__db_copy(req, data){
    $('#d_cb_all').attr('checked', false);
    $('input.SHFT_cb').attr('checked', false);
    $('#db_copy_select').val('0');
    $('#databrowser tr').removeClass('shared');
    switch_menus(true);
}
function resp__check_version(req, data){
    $('div[rel=check_version] div').append(data);
}
function resp__check_export(req, data){
    iframe_download( 'export', req.db, req.id );
}
function resp__ph_dos(req, data){
    dos_plotter(req, data, 'ph_dos-holder', {x: 'Frequency, cm<sup>-1</sup>', y: 'DOS, states/cm<sup>-1</sup>'});
}
function resp__e_dos(req, data){
    dos_plotter(req, data, 'e_dos-holder', {x: 'E - E<sub>f</sub>, eV', y: 'DOS, states/eV'});
}
function resp__ph_bands(req, data){
    bands_plotter(req, data, 'ph_bands-holder', 'Frequency, cm<sup>-1</sup>');
}
function resp__e_bands(req, data){
    bands_plotter(req, data, 'e_bands-holder', 'E - E<sub>f</sub>, eV');
}
/**
*
*
* ======================================================================================================
*
*/
// DOM loading
$(document).ready(function(){
    _tilde.cw = document.body.clientWidth;
    var centerables = ['notifybox', 'loadbox', 'initbox'];
    var centerize = function(){
        $.each(centerables, function(n, i){
        document.getElementById(i).style.left = _tilde.cw/2 - $('#'+i).width()/2 + 'px';
        });
    };
    centerize();
    if (navigator.appName == 'Microsoft Internet Explorer'){
        _tilde.degradation = true;
        //notify('Microsoft Internet Explorer doesn\'t work properly with this page.<br />Please, try to use Chrome, Firefox, Safari or Opera browser.<br />Thank you in advance and sorry for inconvenience.');
    }
    $('#notifybox').hide();

    // initialize client-side settings
    _tilde.settings = $.jStorage.get('tilde_settings', _tilde.default_settings);
    _tilde.maxcols = Math.round(_tilde.cw/160) || 2;
    if (_tilde.settings.cols.length > _tilde.maxcols) _tilde.settings.cols.splice(_tilde.maxcols-1, _tilde.settings.cols.length-_tilde.maxcols+1);
/**
*
*
* ======================================================================================================
*
*/
    _tilde.socket = new io.connect( location.hostname, { transports: ['websocket', 'xhr-polling'], reconnect: true } );

    _tilde.socket.on('connect', function(){
        logger('CONNECTED.');
        $('#notifybox').hide();
        _tilde.freeze = false;
        __send('login',  {settings: _tilde.settings} );
    });

    _tilde.socket.on('message', function(data){
        var split = data.split( _tilde.wsock_delim );
        var response = {};
        response.act = split[0];
        response.req = split[1].length ? $.evalJSON(split[1]) : {};
        response.error = split[2];
        response.data = split[3];
        if (_tilde.debug) logger('RECEIVED: '+response.act);
        if (response.act != 'report' || response.req.directory < 1){ _tilde.freeze = false; $('#loadbox').hide(); } // global lock for multireceive
        if (response.error && response.error.length>1){
            notify('Diagnostic message:<br />'+response.error);
            return;
        }
        if (window['resp__' + response.act]) window['resp__' + response.act](response.req, response.data);
        else notify('Unhandled action received: ' + response.act);
    });

    _tilde.socket.on('error', function(data){
        if (_tilde.debug) logger('AN ERROR IN SOCKET HAS OCCURED!');
    });

    _tilde.socket.on('disconnect', function(data){
        logger('CONNECTION WITH PROGRAM CORE WAS LOST!');
        if (_tilde.debug){
            notify('Program core does not respond. Please, try to <a href=javascript:document.location.reload()>restart</a>.');
        } else {
            _tilde.socket.socket.reconnect();
        }
    });

    _tilde.socket.on('reconnect_failed', function(){
        notify('Connection to program core cannot be established due to the network restrictions. Sometimes <a href=javascript:window.location.reload()>refresh</a> may help.');
    });

/**
*
*
* ======================================================================================================
*
*/
    // STATE FUNCTIONALITY GIVEN BY ANCHORS
    setInterval(function(){
    if (_tilde.cur_anchor != document.location.hash){
        _tilde.cur_anchor = document.location.hash;

        var anchor = _tilde.cur_anchor.substr(1);

        if (_tilde.freeze){ _tilde.cur_anchor = null; return; } // freeze and wait for server responce if any command is given

        switch_menus(true);

        if (anchor == 'start'){
            if (_tilde.protected){
                document.location = '/static/demo.html';
            } else {
                $('div.pane').hide();
                $('#landing_holder').show();
                $("#tilde_logo").animate({ marginTop: '20px' }, { duration: 250, queue: false });
                $("#mainframe").animate({ height: 'show' }, { duration: 250, queue: false });
            }
        }
        else if (anchor == 'continue'){
            $('div.pane').hide();
            $('#splashscreen_holder').hide();
            $('#noclass_trigger').hide();
            $('#data_holder').show();
            $('#databrowser').show();
        }
        else if (anchor == 'browse'){
            $('div.pane').hide();
            $('#splashscreen_holder').hide();
            $('#closeobj_trigger').hide();

            $('#data_holder').show();

            if ($('#splashscreen div').length){
                $('#tagcloud_trigger').show();
                $('#noclass_trigger').show();
            } else {
                _tilde.timeout1 = setInterval(function(){
                    if (!_tilde.freeze){
                        __send('tags', {tids: false, render: 'splashscreen', switchto: 'tags'});
                        clearInterval(_tilde.timeout1);
                    }
                }, 500);
            }
            _tilde.sortdisable = false; // sorting switch
        }
        else if (anchor == 'tags'){
            $('div.pane').hide();
            $('#databrowser').hide();
            $('div.downscreen').hide();
            $('#countbox').hide();

            $('#tagcloud_trigger').hide();
            $('#closeobj_trigger').hide();
            $('#noclass_trigger').hide();

            if (!$('#splashscreen div').length){
                _tilde.timeout2 = setInterval(function(){
                if (!_tilde.freeze){
                    __send('tags', {tids: false, render: 'splashscreen', switchto: 'tags'});
                    clearInterval(_tilde.timeout2);
                }
                }, 500);
            } else {
                $('#data_holder').show();
                $('#splashscreen_holder').show();
                //add_tag_expanders();
            }
            _tilde.rendered = {}; // reset objects
            _tilde.tab_buffer = [];
            $('tr.obj_holder').remove();
            $('#data_holder').show();
        }
        else if (anchor.length > 55){
            $('#connectors').hide();
            $('div.pane').hide();
            $('#splashscreen_holder').hide();

            $('#data_holder').show();
            $('#databrowser').show();
            $('#tagcloud_trigger').show();
            $('#noclass_trigger').show();

            var hashes = anchor.split('+');

            if (!$('#databrowser td').length){
                _tilde.timeout3 = setInterval(function(){
                    if (!_tilde.freeze){
                        __send('browse', {hashes: hashes} );
                        clearInterval(_tilde.timeout3);
                    }
                }, 500);
            } else {
                $.each(hashes, function(n, i){
                    if (!_tilde.rendered[i] && i.length == 56) {
                        var obf = $('<tr class=obj_holder></tr>').append( $('<th colspan=20></th>').append( $('#object_factory').clone().removeAttr('id').attr('id', 'o_'+i) ) );
                        $('#i_'+i).after(obf);
                        __send('summary',  {datahash: i} )
                        open_ipane('summary', i);
                        _tilde.rendered[i] = true;
                        _tilde.scrollmemo = $('#i_'+i).offset().top;
                        $('html, body').animate({scrollTop: _tilde.scrollmemo - 54});
                    }
                });
            }
            _tilde.sortdisable = true; // sorting switch
        }
    }
    }, 333);
/**
*
*
* ======================================================================================================
*
*/
    // FILETREE DIR PROCESSOR
    $(document).on('click', 'div.filetree span.mult_read', function(){
        var $el = $(this), rel = $el.attr("rel"), rev = $el.attr("rev");
        $el.parent().children('span').hide();
        $el.after('<span rel=__read__'+rel+'>scan in progress...</span>');
        $el.remove();
        if (rev) __send('report',  {path: rel, directory: 2, transport:'local'} );
        else     __send('report',  {path: rel, directory: 1, transport:'local'} );
        $('#tagcloud_holder').hide();
        $('#debug-holder').show();
    });

    // INTRO TRIGGER
    $('#continue_trigger').click(function(){
        if ($(this).attr('rel') == 'start_junction') var action = function(){ __send('browse', {}); }
        else var action = function(){ document.location.hash = '#tags'; }

        $("#tilde_logo").animate({ marginTop: '175px' }, { duration: 330, queue: false });
        $("#mainframe").animate({ height: 'hide' }, { duration: 330, queue: false, complete: function(){ action() } });
    });

    // REPORT DONE TRIGGER
    $(document).on('click', 'span.scan_done_trigger', function(){
        $('#connectors').hide();
    });
    $(document).on('click', 'span.scan_details_trigger', function(){
        $('#debug-button').trigger('click');
    });

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
    $(document).on('click', 'div._destroy', function(){
        var id = $(this).parent().parent().parent().attr('id').substr(2);

        close_obj_tab(id);

        var hashes = document.location.hash.substr(1).split('+');
        var i = $.inArray(id, hashes);
        hashes.splice(i, 1);
        if (!hashes.length) document.location.hash = '#browse';
        else document.location.hash = '#' + hashes.join('+');
        $('html, body').animate({scrollTop: _tilde.scrollmemo - 54});
    });

    // DEBUG CONSOLE
    $('#debug-button').click(function(){
        $('#tagcloud_holder').hide();
        if ($('#debug-holder').is(':visible')) $('#debug-holder').animate({ height: 'hide' }, { duration: 250, queue: false });
        else $('#debug-holder').animate({ height: 'show' }, { duration: 250, queue: false });
    });

    // DATABROWSER TABLE
    $(document).on('click', '#databrowser td', function(){
        if ($(this).parent().attr('id')) var id = $(this).parent().attr('id').substr(2);
        else return;
        if (_tilde.rendered[id]) {
            // close tab
            close_obj_tab(id);

            var hashes = document.location.hash.substr(1).split('+');
            var i = $.inArray(id, hashes);
            hashes.splice(i, 1);
            if (!hashes.length) document.location.hash = '#browse';
            else document.location.hash = '#' + hashes.join('+');
        } else {
            // open tab
            var size = 0, key;
            for (key in _tilde.rendered){
                if (_tilde.rendered[key]) size++;
            }
            if (size == 3){
                // remove the first tab
                var hashes = document.location.hash.substr(1).split('+');
                var first = hashes.splice(0, 1);

                close_obj_tab(first);

                document.location.hash = '#' + hashes.join('+');
            }
            if (document.location.hash.length > 55){
                document.location.hash += '+' + id
            } else document.location.hash = '#' + id;
            $('#closeobj_trigger').show();
        }
        $('div.downscreen').hide();
        $('html, body').animate({scrollTop: _tilde.scrollmemo - 54});
    });

    // DATABROWSER CHECKBOXES
    $(document).on('click', 'input.SHFT_cb', function(event){
        event.stopPropagation();
        if ($(this).is(':checked')) $(this).parent().parent().addClass('shared');
        else $(this).parent().parent().removeClass('shared');

        var flag = false;
        $('input.SHFT_cb').each(function(){
            if ($(this).is(':checked')) { flag = true; return false }
        });
        if (flag) switch_menus();
        else switch_menus(true);
    });
    $(document).on('click', '#d_cb_all', function(){
        if ($(this).is(':checked') && $('#databrowser td').length > 1) {
            $('input.SHFT_cb').prop('checked', true);
            $('#databrowser tr').addClass('shared');
            switch_menus();
        } else {
            $('input.SHFT_cb').prop('checked', false);
            $('#databrowser tr').removeClass('shared');
            switch_menus(true);
        }
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
    
    // CANCEL CONTEXT MENU
    $('#cancelctx_trigger').click(function(){
        $('input.SHFT_cb, #d_cb_all').prop('checked', false);
        $('#databrowser tr').removeClass('shared');
        switch_menus(true);
    });
    
    // EXPORT DATA FUNCTIONALITY
    $('#export_trigger').click(function(){
        if ($('#databrowser tr.shared').length == 1){
            var id = $('#databrowser tr.shared').attr('id').substr(2);
            __send('check_export', {id: id, db: _tilde.settings.dbs[0]});
        } else notify('Batch export is not implemented.');
    });

    // DATABROWSER MENU ADD
    $(document).on('click', '#add_trigger, span.add_trigger', function(){
        $('div.downscreen').hide();
        $('#connectors').css('left', (_tilde.cw - $('#connectors').width() )/2 + 'px').show();
        $('html, body').animate({scrollTop: 0});
        open_ipane('conn-local');
        if (!_tilde.filetree.transports['local']){
            $("#tilda-local-filetree").html('<ul class="jqueryFileTree start"><li class="wait">' + _tilde.filetree.load_msg + '</li></ul>');
            __send('list',   {path:_tilde.filetree.root, transport:'local'} );
        }
    });
    $('#noclass_trigger').click(function(){
        $('#tagcloud_trigger').hide();
        $(this).hide();
        $('#splashscreen').empty();
        document.location.hash = '#tags';
    });
    $('#closeobj_trigger').click(function(){
        $(this).hide();
        var hashes = document.location.hash.substr(1).split('+');
        $.each(hashes, function(n, i){
            close_obj_tab(i);
        });
        document.location.hash = '#browse';
        $('html, body').animate({scrollTop: _tilde.scrollmemo - 54});
    });
    $('#tagcloud_trigger').click(function(){
        $('#debug-holder').hide();
        if ($('#tagcloud_holder').is(':visible')) $('#tagcloud_holder').animate({ height: 'hide' }, { duration: 250, queue: false });
        else $('#tagcloud_holder').animate({ height: 'show' }, { duration: 250, queue: false });
    });

    // SPLASHSCREEN TAGCLOUD EXPANDERS
    $(document).on('click', 'a.tagmore', function(){
        $(this).parent().removeClass('tagarea_reduced').append('<a class=tagless href=#>&larr;</a>');
        $(this).remove();
        return false;
    });
    $(document).on('click', 'a.tagless', function(){
        $(this).parent().addClass('tagarea_reduced');
        add_tag_expanders();
        $(this).remove();
        return false;
    });


    // TAGCLOUD TAG COMMANDS SINGLE CLICK
    // immediate data request and consequent tags request
    $(document).on('click', '#tagcloud a.taglink', function(){
        $('#tagcloud').hide();

        var tags = gather_tags($('#tagcloud'), $(this));
        if (tags.length){
            __send('browse', {tids: tags, defer_load: true});
            _tilde.rendered = {}; // reset objects
            _tilde.tab_buffer = [];
        } else {
            $('#splashscreen').empty();
            document.location.hash = '#tags';
        }
        return false;
    });

    // SPLASHSCREEN TAG COMMANDS SINGLE CLICK
    // immediate tags request and ability for consequent data request
    $(document).on('click', '#splashscreen a.taglink', function(){
        var tags = gather_tags($('#splashscreen'), $(this));
        if (tags.length){
            __send('tags', {tids: tags, render: 'splashscreen', switchto: false});
        } else {
            __send('tags', {tids: false, render: 'splashscreen', switchto: false});
            $('#initbox').hide();
        }
        return false;
    });

    // SPLASHSCREEN INIT TAG QUERY
    $('#init_trigger').click(function(){
        var tags = gather_tags($('#splashscreen'));
        __send('browse', {tids: tags});
        _tilde.rendered = {}; // reset objects
        _tilde.tab_buffer = [];
        $('#initbox').hide();
    });

    // IPANE COMMANDS
    $(document).on('click', 'ul.ipane_ctrl li', function(){
        var cmd = $(this).attr('rel');
        if (_tilde.freeze && !_tilde.tab_buffer[cmd]){ notify(_tilde.busy_msg); return; }
        var target = $(this).parents('.object_factory_holder');
        target = (target.length) ? target.attr('id').substr(2) : false;
        open_ipane(cmd, target);
    });

    // PHONONS TABLE
    //$('th.thsorter').click(function(){
    //    $('td.white span').removeClass('hdn');
    //});
    $(document).on('click', 'div.ph_degenerated_trigger', function(){
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
    $(document).on('click', 'div.ph_animate_trigger', function(){
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

    // SETTINGS: GENERAL TRIGGERS
    $('#left_half_gear, #right_half_gear, #settings_trigger').click(function(){
        if ($('#profile_holder').is(':visible')){
            $('#profile_holder').hide();
        } else {
            $('#profile_holder').show();
            open_ipane('admin');
        }
    });

    // SETTINGS: DATABASE MANAGEMENT
    $(document).on('click', '#metablock span, h1 span', function(){
        if ($('#profile_holder').is(':visible')){
            $('#profile_holder').hide();
        } else {
            $('#profile_holder').show();
            open_ipane('dbs');
        }
    });

    // SETTINGS: CLICKS ON DATABASES
    $(document).on('click', 'div.db-make-active-trigger', function(){
        var active_db = $(this).parent().attr('rel');
        __send('settings',  {area: 'switching', switching: active_db} );
    });
    $(document).on('click', 'div.db-delete-trigger', function(){
        var $e = $(this);
        $e.html('confirm').removeClass('db-delete-trigger').addClass('db-delete-confirm-trigger');
        setTimeout(function(){ $e.html('delete').removeClass('db-delete-confirm-trigger').addClass('db-delete-trigger') }, 2000);
    });
    $(document).on('click', 'div.db-delete-confirm-trigger', function(){
        var db = $(this).parent().attr('rel');
        __send('clean',  {db: db} );
    });
    $(document).on('click', '#create-db-trigger', function(){
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
    $(document).on('click', '#ipane_cols_holder > ul > li > input', function(){
        if ($('#ipane_cols_holder > ul > li > input:checked').length > _tilde.maxcols){
            $('#maxcols').parent().css('background-color', '#f99');
            return false;
        }
        $('#maxcols').parent().css('background-color', '#fff');
    });

    // SETTINGS: EXPLICIT CLICK TO SAVE
    $('div.settings-apply').click(function(){
        if ($('#settings_local_path').is(':visible')){

            // SETTINGS: SCAN
            _tilde.settings.local_dir = $('#settings_local_path').val();
            $('#settings_quick_regime').is(':checked')  ? _tilde.settings.quick_regime = 1 : _tilde.settings.quick_regime = 0;
            $('#settings_skip_unfinished').is(':checked')        ? _tilde.settings.skip_unfinished = 1 : _tilde.settings.skip_unfinished = 0;
            $('#settings_skip_if_path').is(':checked')  ? _tilde.settings.skip_if_path = $('#settings_skip_if_path_mask').val() : _tilde.settings.skip_if_path = 0;

            __send('settings',  {area: 'scan', settings: _tilde.settings} );
        } else if ($('#ipane_cols_holder').is(':visible')){

            // SETTINGS: COLS
            var sets = [];
            $('#ipane_cols_holder > ul > li > input').each(function(){
                if ($(this).is(':checked')) sets.push( parseInt( $(this).attr('value') ) );
            });
            _tilde.settings.cols = sets;
            $('#ipane-maxitems-holder > input').each(function(){
                if ($(this).is(':checked')){
                    _tilde.settings.colnum = parseInt( $(this).attr('value') );
                }
            });
            __send('settings', {area: 'cols', settings: _tilde.settings} );
            $('#profile_holder').hide();
        }        
    });

    // UNIVERSAL ENTER HOTKEY: NOTE ACTION BUTTON *UNDER THE SAME DIV* WITH THE FORM
    $(document).on('submit', 'form._hotkeyable', function(){
        $(this).parent().children('div._hotkey').trigger("click");
        return false;
    });

    // SETTINGS: UNITS
    $(document).on('click', '#ipane-units-holder > input', function(){
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

    // SETTINGS: RESTART + TERMINATE
    $('#core-restart').click(function(){
        if (_tilde.freeze){ notify(_tilde.busy_msg); return; }
        __send('restart');
        //logger('RESTART SIGNAL SENT');
        //notify('Core is restarting... <a href=javascript:document.location.reload()>Reload page?</a>');
        setInterval(function(){document.location.reload()}, 2000); // setTimeout doesn't work here
    });
    $('#core-terminate').click(function(){
        if (_tilde.freeze){ notify(_tilde.busy_msg); return; }
        __send('terminate');
        logger('TERMINATE SIGNAL SENT');
        notify('This window is not functional now.');
    });
    $('#ui-restart').click(function(){ document.location.reload() });

    // SETTINGS: USABILITY
    /* $('#profile_holder').mouseleave(function(){
        _tilde.timeout4 = setTimeout(function(){ $('#profile_holder').hide() }, 1500);
    });
    $('#profile_holder').mouseenter(function(){
        clearTimeout(_tilde.timeout4);
    }); */

    // ABOUT
    $('#about_trigger').click(function(){
        document.location.hash = '#start';
        if ($('#splashscreen div').length) $('#continue_trigger').removeAttr('rel');
    });

    // RESIZE
    $(window).resize(function(){
        if (Math.abs(_tilde.cw - document.body.clientWidth) < 30) return; // width of scrollbar
        _tilde.cw = document.body.clientWidth;
        centerize();
        add_tag_expanders();
        _tilde.maxcols = Math.round(_tilde.cw/160) || 2;
        $('#maxcols').html(_tilde.maxcols);
    });

    // ESC KEY
    $(document).keyup(function(e){
        if (e.keyCode == 27){ $('div._closable').hide(); }
    });
});