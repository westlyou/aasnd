
$(function() {

    var scanable = true; //是否可以继续扫描

    $(document).on('click', 'li.station', function(e){
        var station = $(this);
        var stationid = station.attr('stationid');
        var stationname = station.attr('stationname');
        $('#cstation').attr('stationid', stationid).html(stationname);
        action_loading_equipments(parseInt(stationid));
    });

    //员工牌扫描
    new VScanner(function(barcode){
        if(barcode==null || barcode==''){
            layer.msg('扫描条码异常！', {icon: 5});
            return ;
        }
        var prefix = barcode.substring(0,2);
        if(prefix!='AM'){
            layer.msg('扫描异常，请确认是否在扫描员工工牌条码！', {icon: 5});
            return ;
        }
         var action = $('#workstationlist').attr('action');
        if(action=='leave'){
            layer.msg('当前离岗还未选择离岗原因；暂时不可以继续操作！', {icon: 5});
            return ;
        }
        var scanparams = {'barcode': barcode};
        var cstationid = parseInt($('#cstation').attr('stationid'));
        if(cstationid > 0){
            scanparams['stationid'] = cstationid;
        }
        var cequipmentid = parseInt($('#cequipment').attr('equipmentid'));
        if(cequipmentid > 0){
            scanparams['equipmentid'] = cequipmentid;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/attendance/actionscan',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#cemployee').attr('employeeid', dresult.employee_id).html(dresult.employee_name);
                if(dresult.action=='leave'){
                    action_leave(dresult.attendance_id);
                    return ;
                }
                if(dresult.message!='' && dresult.message!=null){
                    // 显示信息后刷新页面！
                    layer.msg(dresult.message, {icon: 1}, function(){
                        window.location.reload(true);
                    });
                    return ;
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

    function refreshstations(){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/attendance/refreshstations',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {}, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#workstationlist').html('');
                if(dresult.workstations.length<=0){
                    return ;
                }
                $.each(dresult.workstations, function(index, station){
                    var stationblock = $('<div class="col-md-3"></div>').appendTo($('#workstationlist'));
                    var stationcontent = $('<div class="box box-widget widget-user-2"></div>').appendTo(stationblock);
                    var stationheader = $('<div class="widget-user-header"></div>').appendTo(stationcontent);
                    if (station.station_type=='scanner'){
                        stationheader.addClass('bg-aqua');
                    }else{
                        stationheader.addClass('bg-green');
                    }
                    stationheader.html('<h3 class="widget-user-username" style="margin-left:0;">'+station.station_name+'</h3>');
                    var stationfooter = $('<div class="box-footer no-padding"></div>').appendTo(stationcontent);
                    var footerbox = $('<ul class="nav nav-stacked"></ul>').appendTo(stationfooter);
                    $.each(station.employees, function(tindex, semployee){
                        $('<li><a href="#" style="font-size:18px; padding:5px 15px; height:32px; font-weight:bold;">' +
                            semployee.employee_name+'<span class="pull-right">'+semployee.employee_code+'</span>' +
                            '</a></li>').appendTo(footerbox);
                    });
                });
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });
    }
    // 20秒刷新一次工位看板
    var refreshinterval = setInterval(_.throttle(refreshstations, 20000), 20000);


    function action_leave(attendanceid){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/attendance/loadingleavelist',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {}, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.leavelist.length > 0){
                    initleavelisthtml(attendanceid, dresult.leavelist);
                }else{
                    layer.msg('您已离岗！', {icon: 1});
                    window.location.reload(true);
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });
    }

    function initleavelisthtml(attendanceid, leavelist){
        $('#workstationlist').attr('action', 'leave');
        var tcontent = '<div class="row" style="margin-top: 10px;clear: both;zoom: 1; padding:0px 20px;">';
        $.each(leavelist, function(index, tleave){
            tcontent += '<div class="col-md-4">';
            tcontent += '<a href="javascript:void(0);" class="btn btn-block btn-success aas-leave" ';
            tcontent += 'style="margin-top:10px;margin-bottom:10px; height:100px; line-height:100px; font-size:25px; padding:0;" ';
            tcontent += 'leaveid='+tleave.leave_id+'>'+tleave.leave_name+'</a>';
            tcontent += '</div>';
        });
        tcontent += '</div>';
        var lindex = layer.open({
            type: 1,
            closeBtn: 0,
            skin: 'layui-layer-rim',
            title: '请在下面选择您的离岗原因',
            area: ['980px', '560px'],
            content: tcontent
        });
        $('.aas-leave').click(function(){
            var self = $(this);
            var leaveid = parseInt(self.attr('leaveid'));
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var lparams = {'attendanceid': attendanceid, 'leaveid': leaveid};
            $.ajax({
                url: '/aasmes/attendance/actionleave',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: lparams, id: access_id}),
                success:function(data){
                    $('#workstationlist').attr('action', 'working');
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    // layer.close(lindex);
                    window.location.reload(true);
                },
                error:function(xhr,type,errorThrown){
                    console.log(type);
                    $('#workstationlist').attr('action', 'working');
                }
            });

        });
    }


    function action_loading_equipments(workstationid){
        var temparams = {'workstationid': workstationid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/attendance/workstation/equipmentlist',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var equipmentrow = $('#equipmentlist');
                equipmentrow.html('');
                if(dresult.equipmentlist.length <= 0){
                    return ;
                }
                $.each(dresult.equipmentlist, function(index, tequipment){
                    var titem = $('<div class="col-md-3 col-xs-6 aas-equipment"></div>');
                    titem.attr({'eid': tequipment.equipment_id, 'ecode': tequipment.equipment_code});
                    titem.css({'cursor': 'pointer', 'margin-bottom': '10px'});
                    var tempstr = '<div class="small-box bg-green" style="margin-bottom:0;">';
                    tempstr += '<div class="inner" style="text-align:center;">';
                    tempstr += '<h4>'+tequipment.equipment_name+'</h4><p>'+tequipment.equipment_code+'</p></div></div>';
                    titem.html(tempstr).appendTo(equipmentrow);
                    titem.click(function(){
                        $('#cequipment').attr('equipmentid', tequipment.equipment_id).html(tequipment.equipment_code);
                    });
                });
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });
    }

    $('.aas-equipment').click(function(){
        var eid=$(this).attr('eid');
        var ecode = $(this).attr('ecode');
        $('#cequipment').attr('equipmentid', eid).html(ecode);
    });



});