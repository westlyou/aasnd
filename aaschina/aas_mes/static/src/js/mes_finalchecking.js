/**
 * Created by luforn on 2017-11-4.
 */

$(function(){

    var nativeSpeech = new SpeechSynthesisUtterance();
    nativeSpeech.lang = 'zh';
    nativeSpeech.rate = 1.2;
    nativeSpeech.pitch = 1.5;
    nativeSpeech.volume = 1.0;

    function nativespeak(message){
        nativeSpeech.text = message;
        speechSynthesis.speak(nativeSpeech);
    }

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
                    if(dresult.needrole){
                        // layer.msg(dresult.message, {icon: 1});
                        initcheckingrolehtml(dresult.employee_id);
                    }else{
                        changeemployeerole(dresult.employee_id, 'check');
                    }
                }else{
                    action_leave(dresult.attendance_id);
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    function initcheckingrolehtml(employeeid){
        var tcontent = '<div class="row" style="margin-top: 10px;clear: both;zoom: 1; padding:0px 20px;">';

        tcontent += '<div class="col-md-6">';
        tcontent += '<a href="javascript:void(0);" class="btn btn-block btn-success aas-action" ';
        tcontent += 'style="margin-top:10px;margin-bottom:10px; height:100px; line-height:100px; font-size:25px; padding:0;" ';
        tcontent += 'actiontype="scan">扫描</a>';
        tcontent += '</div>';

        tcontent += '<div class="col-md-6">';
        tcontent += '<a href="javascript:void(0);" class="btn btn-block btn-success aas-action" ';
        tcontent += 'style="margin-top:10px;margin-bottom:10px; height:100px; line-height:100px; font-size:25px; padding:0;" ';
        tcontent += 'actiontype="check">终检</a>';
        tcontent += '</div>';

        tcontent += '</div>';
        var lindex = layer.open({
            type: 1,
            closeBtn: 0,
            skin: 'layui-layer-rim',
            title: '请在下面选择您的角色',
            area: ['490px', '250px'],
            content: tcontent
        });
        $('.aas-action').click(function(){
            var self = $(this);
            changeemployeerole(employeeid, self.attr('actiontype'));
        });
    }

    function changeemployeerole(employeeid, role){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var tparams = {'employeeid': employeeid, 'action_type': role};
        $.ajax({
            url: '/aasmes/finalchecking/changemployeerole',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: tparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
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
                $('#reworklist').html('');
                $('#operationlist').html('');
                $('#checkwarning').html(dresult.message);
                $('#customercode').html(dresult.customer_code);
                $('#internalcode').html(dresult.internal_code);
                $('#ctserialnumber').html(barcode).attr('serialnumber', barcode);
                $('#informationlist').attr({'operationid': dresult.operationid});
                action_init_record_rework(dresult.recordlist, dresult.reworklist);
                if(!dresult.success){
                    $('#final_result_box').removeClass('bg-green').addClass('bg-red');
                    $('#final_result_content').html('N G');
                    nativespeak($('#checkwarning').html());
                    return ;
                }
                $('#final_result_content').attr('serialcount', dresult.serialcount).html(dresult.serialcount);
                if($('#final_result_box').hasClass('bg-red')){
                    $('#final_result_box').removeClass('bg-red').addClass('bg-green');
                }
                if(dresult.rework){
                    nativespeak($('#checkwarning').html());
                    $('#final_result_content').html('重工');
                    action_reworkconfirm(dresult.badmode_name);
                }else{
                    if(dresult.done){
                        nativespeak($('#checkwarning').html());
                    }else{
                        nativespeak($('#final_result_content').html());
                    }
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //返工确认
    function action_reworkconfirm(badmode){
        var warnmessage = badmode+'不良返工， 是否确认PASS？';
        layer.confirm(warnmessage, {'btn': ['确认', '取消']}, function(index){
            layer.close(index);
            var operationid = parseInt($('#informationlist').attr('operationid'));
            if(operationid<=0){
                layer.msg('您还没有扫描条码，暂不可以操作！', {icon: 5});
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
                    action_loadrecordlist();
                },
                error:function(xhr,type,errorThrown){ console.log(type);}
            });
        }, function(){});
    }

    //加载操作记录和返工记录
    function action_loadrecordlist(){
        $('#reworklist').html('');
        $('#operationlist').html('');
        var operationid = parseInt($('#informationlist').attr('operationid'));
        if(operationid <= 0){
            return ;
        }
        var tparams = {'operationid': operationid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/finalchecking/loadrecordlist',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: tparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                action_init_record_rework(dresult.recordlist, dresult.reworklist);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    function action_init_record_rework(recordlist, reworklist){
        $('#reworklist').html('');
        $('#operationlist').html('');
        if(recordlist.length > 0){
            $.each(recordlist, function(index, record){
                var operationtr = $('<tr></tr>');
                if(record.result){
                    $('<td></td>').html('<i class="fa fa-check text-green"></i>').appendTo(operationtr);
                }else{
                    $('<td></td>').html('<i class="fa fa-exclamation text-red"></i>').appendTo(operationtr);
                }
                $('<td></td>').html(record.sequence).appendTo(operationtr);
                $('<td></td>').html(record.operation_name).appendTo(operationtr);
                $('<td></td>').html(record.operation_time).appendTo(operationtr);
                $('<td></td>').html(record.equipment_code).appendTo(operationtr);
                $('<td></td>').html(record.scan_employee).appendTo(operationtr);
                $('<td></td>').html(record.employee_name).appendTo(operationtr);
                $('#operationlist').append(operationtr);
            });
        }
        if(reworklist.length > 0){
            $.each(reworklist, function(index, record){
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
    }

    /*$('#action_consume').click(function(){
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
    });*/

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
                    window.location.reload(true);
                },
                error:function(xhr,type,errorThrown){ console.log(type); }
            });
        });
    }

    function action_loading_serialcount(){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/finalchecking/serialcount',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {}, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#final_result_content').attr('serialcount', dresult.serialcount).html(dresult.serialcount);
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }

    //刷新页面显示扫描成品数量
    action_loading_serialcount();

});
