/**
 * Created by luforn on 2017-11-4.
 */

$(function(){

    new VScanner(function(barcode){
        if(barcode==null || barcode==''){
            layer.msg('扫描条码异常！', {icon: 5});
            return ;
        }
        var prefix = barcode.substring(0,2);
        if(prefix=='AM'){
            action_scanemployee(barcode);
        }else{
            action_scanserialnumber(barcode);
        }
    });

    //扫描员工卡
    function action_scanemployee(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/finalchecking/scanemployee',
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
                    layer.msg(dresult.message, {icon: 1});
                }
                if(dresult.action=='working'){
                    var templi = $('<li class="cemployee" id="employee_'+dresult.employee_id+'"></li>');
                    templi.html('<a href="javascript:void(0);">'+dresult.employee_name+'<span class="pull-right">'+dresult.employee_code+'</span></a>');
                    $('#finalchecking_employees').append(templi);
                }else{
                    $('#employee_'+dresult.employee_id).remove();
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //扫描序列号
    function action_scanserialnumber(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/finalchecking/scanserialnumber',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#checkwarning').html('');
                $('#operationlist').html('');
                $('#ctserialnumber').html(dresult.serialnumber);
                $('#action_confirm').attr({
                    'checkval': dresult.checkval, 'operationid': dresult.operationid
                });
                if(dresult.message){
                    $('#checkwarning').html(dresult.message);
                }
                if(dresult.rework){
                    $('#serialrework').html('是').attr('class', 'pull-right text-red');
                }else{
                    $('#serialrework').html('否').attr('class', 'pull-right text-green');
                }
                $('#customercode').html(dresult.customer_code);
                $('#internalcode').html(dresult.internal_code);
                $.each(dresult.recordlist, function(index, record){
                    var operationtr = $('<tr></tr>');
                    if(record.result){
                        $('<td></td>').html('<i class="fa fa-check text-green"></i>').appendTo(operationtr);
                    }else{
                        $('<td></td>').html('<i class="fa fa-exclamation text-red"></i>').appendTo(operationtr);
                    }
                    $('<td></td>').html(record.sequence).appendTo(operationtr);
                    $('<td></td>').html(record.operation_name).appendTo(operationtr);
                    $('<td></td>').html(record.equipment_code).appendTo(operationtr);
                    $('<td></td>').html(record.employee_name).appendTo(operationtr);
                    $('<td></td>').html(record.operation_time).appendTo(operationtr);
                    $('#operationlist').append(operationtr);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //终检确认
    $('#action_confirm').click(function(){
        var workorderid = parseInt($('#mes_workorder').attr('workorderid'));
        if(workorderid==0){
            layer.msg('当前产线还未分配工单，暂不可以操作！', {icon: 5});
            return ;
        }
        var employeelist = $('.cemployee');
        if(employeelist==undefined || employeelist==null || employeelist.length<=0){
            layer.msg('当前工位上没有员工，不可以确认操作，请先扫描工牌上岗！', {icon: 5});
            return ;
        }
        var operationid = parseInt($(this).attr('operationid'));
        if(operationid==0){
            layer.msg('您还没有扫描条码，暂不可以操作！', {icon: 5});
            return ;
        }
        var checkval = $(this).attr('checkval');
        if(checkval=='forbidden'){
            layer.msg('请仔细检查是否还有操作未完成！', {icon: 5});
            return ;
        }else if(checkval=='done'){
            layer.msg('当前条码已经确认，请不要重复操作！', {icon: 5});
            return ;
        }
        var scanparams = {'operationid': operationid, 'workorderid': workorderid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/finalchecking/actionconfirm',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.message){
                    layer.msg(dresult.message, {icon: 5});
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

    $('#action_consume').click(function(){
        layer.confirm('您确认是要操作班次结单？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            $.ajax({
                url: '/aasmes/finalchecking/actionconsume',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {}, id: access_id}),
                success:function(data){
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    if(dresult.message){
                        layer.msg(dresult.message, {icon: 5});
                    }
                    window.location.reload(true);
                },
                error:function(xhr,type,errorThrown){ console.log(type);}
            });
        }, function(){});
    });

});
