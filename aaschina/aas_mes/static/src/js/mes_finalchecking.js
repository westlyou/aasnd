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
                    action_leave(dresult.attendance_id);
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
                $('#ctserialnumber').html(dresult.serialnumber).attr('serialnumber', barcode);
                $('#informationlist').attr({'checkval': dresult.checkval, 'operationid': dresult.operationid});
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
                if(dresult.recordlist.length > 0){
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
                }
                if(dresult.reworklist.length > 0){
                    $.each(dresult.reworklist, function(index, record){
                        var reworktr = $('<tr></tr>');
                        $('<td></td>').html(index+1).appendTo(reworktr);
                        $('<td></td>').html(record.badmode_name).appendTo(reworktr);
                        $('<td></td>').html(record.badmode_date).appendTo(reworktr);
                        $('<td></td>').html(record.commiter).appendTo(reworktr);
                        $('<td></td>').html(record.commit_time).appendTo(reworktr);
                        $('<td></td>').html(record.repairer).appendTo(reworktr);
                        $('<td></td>').html(record.repair_time).appendTo(reworktr);
                        $('<td></td>').html(record.ipqcchecker).appendTo(reworktr);
                        $('<td></td>').html(record.ipqccheck_time).appendTo(reworktr);
                        $('<td></td>').html(record.state).appendTo(reworktr);
                        $('#reworklist').append(reworktr);
                    });
                }
                if(dresult.checkval=='waiting'){
                    if(dresult.rework){
                        action_reworkconfirm(dresult.badmode_name);
                    }else{
                        action_confirm();
                    }
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //返工确认
    function action_reworkconfirm(badmode){
        var warnmessage = '返工不良模式：'+badmode+'， 是否确认PASS？';
        layer.confirm(warnmessage, {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            var operationid = parseInt($('#informationlist').attr('operationid'));
            if(operationid==0){
                layer.msg('您还没有扫描条码，暂不可以操作！', {icon: 5});
                return ;
            }
            var checkval = $('#informationlist').attr('checkval');
            if(checkval=='forbidden'){
                layer.msg('请仔细检查是否还有操作未完成！', {icon: 5});
                return ;
            }else if(checkval=='done'){
                layer.msg('当前条码已经确认，请不要重复操作！', {icon: 5});
                return ;
            }
            var confirmparams = {'operationid': operationid};
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            $.ajax({
                url: '/aasmes/finalchecking/reworkconfirm',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: confirmparams, id: access_id}),
                success:function(data){
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    var serialnumber = $('#ctserialnumber').attr('serialnumber');
                    if(serialnumber == 0 || serialnumber == '0'){
                        window.location.reload(true);
                    }else{
                        action_scanserialnumber(serialnumber);
                    }
                },
                error:function(xhr,type,errorThrown){ console.log(type);}
            });
        }, function(){});
    }

    //终检确认
    /*$('#action_confirm').click(function(){
        action_confirm();
    });*/

    function action_confirm(){
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
        var operationid = parseInt($('#informationlist').attr('operationid'));
        if(operationid==0){
            layer.msg('您还没有扫描条码，暂不可以操作！', {icon: 5});
            return ;
        }
        var checkval = $('#informationlist').attr('checkval');
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
                var serialnumber = $('#ctserialnumber').attr('serialnumber');
                if(serialnumber == 0 || serialnumber == '0'){
                    window.location.reload(true);
                }else{
                    action_scanserialnumber(serialnumber);
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

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
                        layer.msg(dresult.message, {icon: 1});
                    }
                    window.location.reload(true);
                },
                error:function(xhr,type,errorThrown){ console.log(type);}
            });
        }, function(){});
    });

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
                }
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });
    }

    function initleavelisthtml(attendanceid, leavelist){
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
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    layer.close(lindex);
                },
                error:function(xhr,type,errorThrown){ console.log(type); }
            });

        });
    }

});
