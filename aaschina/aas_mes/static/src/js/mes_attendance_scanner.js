
$(function() {

    $(document).on('click', 'li.station', function(e){
        var station = $(this);
        var stationid = station.attr('stationid');
        var stationname = station.attr('stationname');
        $('#cstation').attr('stationid', stationid);
        $('#cstation').html(stationname);
        var employeeid = parseInt($('#cemployee').attr('employeeid'));
        if(employeeid>0){
            action_working();
        }
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
        var scanparams = {'barcode': barcode};
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
                if(dresult.message!='' && dresult.message!=null){
                    // 显示信息后刷新页面！
                    layer.msg(dresult.message, {icon: 1}, function(){
                        window.location.reload(true);
                    });
                    return ;
                }
                $('#cemployee').attr('employeeid', dresult.employee_id);
                $('#cemployee').html(dresult.employee_name);
                var stationid = parseInt($('#cstation').attr('stationid'));
                if(stationid<=0){
                    layer.msg('员工卡已扫描，请选择工位即可上岗！', {icon: 1});
                    return ;
                }else{
                    action_working();
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

    //上岗
    function action_working(){
        var stationid = parseInt($('#cstation').attr('stationid'));
        var employeeid = parseInt($('#cemployee').attr('employeeid'));
        if(stationid <=0 || employeeid <= 0){
            layer.msg('请确认您是否已经选择了工位和扫描员工卡！', {icon: 5});
            return ;
        }
        var actionparams = {'employeeid': employeeid, 'stationid': stationid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/attendance/actionworking',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: actionparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.message!='' && dresult.message!=null){
                    // 显示信息后刷新页面！
                    layer.msg(dresult.message, {icon: 1}, function(){
                        window.location.reload(true);
                    });
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

});