/**
 * Created by luforn on 2017-11-21.
 */

$(function(){

    var scanable = true; //是否可以继续扫描
    new VScanner(function(barcode) {
        if (barcode == null || barcode == '') {
            scanable = true;
            layer.msg('扫描条码异常！', {icon: 5});
            return;
        }
        var prefix = barcode.substring(0,2);
        if(prefix=='AM'){
            action_scan_employee(barcode);
        }else{
            action_scan_serialnumber(barcode);
        }
    });

    function action_scan_employee(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/reworking/scanemployee',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                scanable = true;
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_employee').attr('employeeid', dresult.employee_id).html(dresult.employee_name);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    function action_scan_serialnumber(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/reworking/scanserialnumber',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                scanable = true;
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if($('#serialnumber_'+dresult.serialnumber_id).length > 0){
                    layer.msg('已扫描，请不要重复操作！', {icon: 5});
                    return ;
                }
                $('#mes_serialnumber').html(barcode);
                $('#mes_productcode').html(dresult.product_code);
                if(dresult.reworklist.length > 0){
                    $.each(dresult.reworklist, function(index, record){
                        var lineno = index + 1;
                        var reworktr = $('<tr></tr>').appendTo($('#rework_list'));
                        $('<td></td>').html(lineno).appendTo(reworktr);
                        $('<td></td>').html(record.serialnumber).appendTo(reworktr);
                        $('<td></td>').html(record.badmode_date).appendTo(reworktr);
                        $('<td></td>').html(record.product_code).appendTo(reworktr);
                        $('<td></td>').html(record.workcenter_name).appendTo(reworktr);
                        $('<td></td>').html(record.badmode_name).appendTo(reworktr);
                        $('<td></td>').html(record.commiter_name).appendTo(reworktr);
                        $('<td></td>').html(record.state_name).appendTo(reworktr);
                    });
                }
                var templi = $('<li class="aas-serialnumber"></li>').attr({
                    'serialnumberid': dresult.serialnumber_id, 'id': 'serialnumber_'+dresult.serialnumber_id
                }).prependTo($('#serialnumberlist'));
                var tempa = $('<a href="javascript:void(0);"></a>').appendTo(templi).append(dresult.serialnumber_name);
                $('<span class="label label-danger pull-right">删除</span>').appendTo(tempa).attr({
                    'serialnumberid': dresult.serialnumber_id
                });
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //删除错误扫描
    $('#serialnumberlist').on('click', 'span.label-danger', function(){
        var serialnumberid = $(this).attr('serialnumberid');
        var templi = $('#serialnumber_'+serialnumberid);
        if(templi!=undefined && templi.length>0){
            templi.remove();
        }
    });

    $('#mes_badmode').select2({
        placeholder: '选择不良模式...',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/badmodelist',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var sparams =  {'q': params.term || '', 'page': params.page || 1};
                return JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sparams, id: Math.floor(Math.random() * 1000 * 1000 * 1000) });
            },
            processResults: function (data, params) {
                params.page = params.page || 1;
                var dresult = data.result;
                return {
                    results: dresult.items,
                    pagination: {more: (params.page * 30) < dresult.total_count}
                };
            }
        }
    });

    $('#mes_workstation').select2({
        placeholder: '选择工位...',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/workstationlist',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var sparams =  {
                    'q': params.term || '', 'page': params.page || 1
                };
                return JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sparams, id: Math.floor(Math.random() * 1000 * 1000 * 1000) });
            },
            processResults: function (data, params) {
                params.page = params.page || 1;
                var dresult = data.result;
                return {
                    results: dresult.items,
                    pagination: {more: (params.page * 30) < dresult.total_count}
                };
            }
        }
    });


    $('#action_commit').click(function(){
        var employeeid = parseInt($('#mes_employee').attr('employeeid'));
        if(employeeid==0){
            layer.msg('你还未扫描员工牌', {icon: 5});
            return ;
        }
        var workstationid = $('#mes_workstation').val();
        if(workstationid==null || workstationid=='' || workstationid==0){
            layer.msg('你还未添加工位，请先选择工位！', {icon: 5});
            return ;
        }
        workstationid = parseInt(workstationid);
        var badmodeid = $('#mes_badmode').val();
        if(badmodeid==null || badmodeid=='' || badmodeid==0){
            layer.msg('你还未添加不良模式，请先选择不良模式！', {icon: 5});
            return ;
        }
        badmodeid = parseInt(badmodeid);
        layer.confirm('您确认是上传不良？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            var serialnumberlist = $('li.aas-serialnumber');
            if(serialnumberlist==undefined || serialnumberlist==null || serialnumberlist.length<= 0){
                layer.msg('你还未扫描不良品！', {icon: 5});
                return ;
            }
            var serialnumberids = [];
            $.each(serialnumberlist, function(index, tserialnumber){
                serialnumberids.push(parseInt($(tserialnumber).attr('serialnumberid')));
            });
            var commitparams = {
                'serialnumberlist': serialnumberids, 'employeeid': employeeid,
                'workstationid': workstationid, 'badmodeid': badmodeid
            };
            scanable = false;
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            $.ajax({
                url: '/aasmes/reworking/actioncommit',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: commitparams, id: access_id}),
                success:function(data){
                    scanable = true;
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    $('#serialnumberlist').html('');
                    $('#rework_list').html('');
                    $('#mes_serialnumber').html('');
                    $('#mes_productcode').html('');
                    $('option', '#mes_badmode').remove();
                    $('#mes_badmode').val('0');
                },
                error:function(xhr,type,errorThrown){
                    scanable = true;
                    console.log(type);
                }
            });
        },function(){});
    });


    $('#action_clearemployee').click(function(){
        layer.confirm('您确定清理员工信息？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            $('#mes_employee').html('').attr('employeeid', '0');
        },function(){});
    });

});
