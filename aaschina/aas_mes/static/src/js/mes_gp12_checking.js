/**
 * Created by luforn on 2017-10-19.
 */

$(function() {

    $('input[type="radio"].flat-blue').iCheck({ checkboxClass: 'icheckbox_flat-blue', radioClass: 'iradio_flat-blue'});

    $('input[type="radio"].flat-blue').on('ifChecked', function(event){
        var labelqty = $(this).attr('qty');
        $('#mes_labelqty').attr('qty', labelqty);
    });

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

    //扫描员工卡
    function action_scan_employee(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/gp12/scanemployee',
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
                if(dresult.message!=null && dresult.message!=''){
                    layer.msg(dresult.message, {icon: 1});
                }
                if(dresult.action=='leave'){
                    var currentemployeeid = $('#mes_operator').attr('employeeid');
                    if (currentemployeeid==dresult.employee_id){
                        $('#mes_operator').attr('employeeid', '0').html('');
                    }
                    $('#employee_'+dresult.employee_id).remove();
                    action_leave(dresult.attendance_id);
                    return ;
                }
                var employeeli = $('<li class="aas-employee"></li>').appendTo($('#employee_list'));
                employeeli.attr('employeeid', dresult.employee_id);
                employeeli.attr({
                    'id': 'employee_'+dresult.employee_id, 'employeeid': dresult.employee_id, 'employeename': dresult.employee_name
                });
                employeeli.html('<a href="javascript:void(0);">'+dresult.employee_name+'</a>');
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //扫描隔离板
    function action_scan_serialnumber(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        var printerid = $('#mes_printer').val();
        if(printerid==null || printerid==''){
            layer.msg('请先设置好标签打印机，再进行扫描操作！', {icon: 5});
            return ;
        }
        scanable = false;
        var employeeid = parseInt($('#mes_operator').attr('employeeid'));
        if(employeeid==0){
            scanable = true;
            var employeelist = $('.aas-employee');
            if(employeelist==undefined || employeelist==null || employeelist.length<=0){
                layer.msg('当前GP12工位还没有员工上岗，请先扫描员工工牌上岗！', {icon: 5});
                return ;
            }
            layer.msg('请在左侧员工列表中选择一个当前操作员工', {icon: 5});
            return ;
        }
        var scanparams = {'barcode': barcode, 'employeeid': employeeid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var customercode = $('#mes_currentpn').attr('customercode');
        if(customercode!=null && customercode!=''){
            scanparams['productcode'] = customercode;
        }
        $.ajax({
            url: '/aasmes/gp12/scanserialnumber',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                scanable = true;
                var dresult = data.result;
                $('#checkwarning').html(dresult.message);
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#check_result').html(dresult.result);
                if(dresult.done){
                    $('#checkwarning').speech({"speech": false, "speed": 6});
                }
                if(dresult.result=='OK'){
                    $('#check_result_box').removeClass('bg-red').addClass('bg-green');
                    var serialnumbertr = $('#serialnumber_'+dresult.serialnumber_id);
                    if(serialnumbertr.length > 0){
                        serialnumbertr.remove();
                    }else{
                        var scount = parseInt($('#pass_count').attr('scount'));
                        scount += 1;
                        $('#pass_count').attr('scount', scount).html(scount);
                        var waitcount = parseInt($('#mes_printbtn').attr('waitcount'));
                        $('#mes_printbtn').attr('waitcount', waitcount+1);
                        $('#pass_count').speech({"speech": false, "speed": 6});
                    }
                    var serialtr = $('<tr></tr>').prependTo($('#pass_list')).html('<td>'+dresult.operate_result+'</td>');
                    serialtr.attr({
                        'class': 'aas-unpack',
                        'serialnumberid': dresult.serialnumber_id, 'id': 'serialnumber_'+dresult.serialnumber_id
                    });
                }else{
                    $('#check_result_box').removeClass('bg-green').addClass('bg-red');
                    $('#fail_list').append('<tr><td>'+dresult.operate_result+'</td></tr>');
                    $('#check_result').html('N G');
                    $('#check_result').speech({"speech": false, "speed": 6});
                }
                if(dresult.message!=null && dresult.message!=''){
                    $('#checkwarning').html(dresult.message);
                }
                var custmoercodespan = $('#mes_currentpn');
                var customercode = custmoercodespan.attr('customercode');
                if(customercode==null || customercode==''){
                    custmoercodespan.attr('customercode', dresult.productcode).html(dresult.productcode);
                }
                $('#functiontest_list').html('');
                if(dresult.functiontestlist.length > 0){
                    $.each(dresult.functiontestlist, function(index, record){
                        var lineno = index+1;
                        var functiontesttr = $('<tr></tr>').appendTo($('#functiontest_list'));
                        $('<td></td>').html(lineno).appendTo(functiontesttr);
                        $('<td></td>').html(record.operate_time).appendTo(functiontesttr);
                        $('<td></td>').html(record.operate_result).appendTo(functiontesttr);
                        $('<td></td>').html(record.operator_name).appendTo(functiontesttr);
                        $('<td></td>').html(record.operate_equipment).appendTo(functiontesttr);
                    });
                }
                $('#rework_list').html('');
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
                        $('<td></td>').html(record.repair_result).appendTo(reworktr);
                        $('<td></td>').html(record.repair_time).appendTo(reworktr);
                        $('<td></td>').html(record.repairer_name).appendTo(reworktr);
                        $('<td></td>').html(record.ipqc_name).appendTo(reworktr);
                    });
                }
                $('#mes_serialnumber').html(barcode);
                var waitcount = parseInt($('#mes_printbtn').attr('waitcount'));
                var labelqty = parseInt($('#mes_labelqty').attr('qty'));
                if(waitcount >= labelqty){
                    action_print_label(labelqty);
                }
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //单击序列号
    $('#pass_list').on('click', 'tr.aas-unpack', function(){
        var serialnumberid = parseInt($(this).attr('serialnumberid'));
        var tparams = {'serialnumberid': serialnumberid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/gp12/loadreworksandrecords',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:30000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: tparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_serialnumber').html(dresult.serialnumber);
                $('#functiontest_list').html('');
                if(dresult.functiontestlist.length > 0){
                    $.each(dresult.functiontestlist, function(index, record){
                        var lineno = index+1;
                        var functiontesttr = $('<tr></tr>').appendTo($('#functiontest_list'));
                        $('<td></td>').html(lineno).appendTo(functiontesttr);
                        $('<td></td>').html(record.operate_time).appendTo(functiontesttr);
                        $('<td></td>').html(record.operate_result).appendTo(functiontesttr);
                        $('<td></td>').html(record.operator_name).appendTo(functiontesttr);
                        $('<td></td>').html(record.operate_equipment).appendTo(functiontesttr);
                    });
                }
                $('#rework_list').html('');
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
                        $('<td></td>').html(record.repair_result).appendTo(reworktr);
                        $('<td></td>').html(record.repair_time).appendTo(reworktr);
                        $('<td></td>').html(record.repairer_name).appendTo(reworktr);
                        $('<td></td>').html(record.ipqc_name).appendTo(reworktr);
                    });
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });

    });

    //自动生成标签并打印
    function action_print_label(serialcount){
        var serialnumberlist = $('.aas-unpack');
        if(serialnumberlist.length <= 0){
            layer.msg('没有成品可以打印标签！', {icon: 5});
            return ;
        }
        if(serialcount <= 0){
            layer.msg('没有成品可以打印标签！', {icon: 5});
            return ;
        }
        var tempqty = 0;
        var serialnumberids = [];
        $.each(serialnumberlist, function(index, serialnumbertr){
            if(tempqty < serialcount){
                serialnumberids.push(parseInt($(serialnumbertr).attr('serialnumberid')));
                tempqty += 1;
            }
        });
        var printerid = parseInt($('#mes_printer').val());
        if(printerid==0){
            layer.msg('您还未选择标签打印机，请先设置好标签打印机！', {icon: 5});
            return ;
        }
        var scanparams = {'serialnumberids': serialnumberids, 'printer_id': printerid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/gp12/dolabel',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_label').html(dresult.label_name);
                action_loading_unpacklist();
                $.each(dresult.records, function(index, record){
                    var params = {'label_name': dresult.printer, 'label_count': 1, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url:'http://'+dresult.serverurl, data: params,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                });
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //标签打印，可能未达到自动打印标签的数量
    $('#mes_printbtn').click(function(){
        var printerid = $('#mes_printer').val();
        if(printerid==null || printerid==''){
            layer.msg('请先设置好标签打印机，再进行打印操作！', {icon: 5});
            return ;
        }
        var waitcount = parseInt($(this).attr('waitcount'));
        if(waitcount==0){
            layer.msg('当前还无法打印标签', {icon: 5});
            return ;
        }
        var labelqty = parseInt($('#mes_labelqty').attr('qty'));
        var tipmessage = '您确认要打印标签吗？';
        if(waitcount < labelqty){
            tipmessage = '当前成品数量少于'+labelqty+',您确认要打印标签吗？';
        }
        layer.confirm(tipmessage, {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            action_print_label(waitcount);
        },function(){});
    });

    //单击员工清单
    $('#employee_list').on('click', '.aas-employee', function(){
        var self = $(this);
        var employeeid = self.attr('employeeid');
        var employeename = self.attr('employeename');
        $('#mes_operator').attr('employeeid', employeeid).html(employeename);
    });

    //上报不良
    $('#action_badmode').click(function(){
        layer.confirm('您确认上报不良？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            var employeeid = parseInt($('#mes_operator').attr('employeeid'));
            if(employeeid==0){
                layer.msg('请在左侧员工列表中选择一个当前操作员工', {icon: 5});
                return ;
            }
            localStorage.setItem('employeeid', employeeid);
            var employeename = $('#employee_'+employeeid).attr('employeename');
            if(employeename!=undefined&&employeename!=null&&employeename!=''){
                localStorage.setItem('employeename', employeename);
            }
            window.open('/aasmes/gp12/rework');
        }, function(){});
    });

    //成品入库
    $('#action_delivery').click(function(){
        layer.confirm('您确认成品出货？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            window.open('/aasmes/gp12/delivery');
        }, function(){});
    });

    $('#mes_printer').select2({
        placeholder: '选择标签打印机...',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/printerlist',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var sparams =  {
                    'q': params.term || '', 'page': params.page || 1
                };
                return JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sparams, id: Math.floor(Math.random() * 1000 * 1000 * 1000) })
            },
            processResults: function (data, params) {
                params.page = params.page || 1;
                var dresult = data.result;
                return {
                    results: dresult.items,
                    pagination: {
                        more: (params.page * 30) < dresult.total_count
                    }
                };
            }
        }
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

    function action_loading_unpacklist(){
        $.ajax({
            url: '/aasmes/gp12/loadunpacklist',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:30000, dataType: 'json',
            data: JSON.stringify({
                jsonrpc: "2.0", method: 'call', params: {}, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
            }),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_currentpn').attr('customercode', dresult.productcode).html(dresult.productcode);
                $('#mes_serialnumber').html(dresult.serialnumber);
                $('#pass_count').attr('scount', dresult.serialcount).html(dresult.serialcount);
                $('#pass_list').html('');
                $('#mes_printbtn').attr('waitcount', dresult.serialcount);
                $('#functiontest_list').html('');
                $('#rework_list').html('');
                if(dresult.serialnumberlist.length < 0){
                    return ;
                }
                $.each(dresult.serialnumberlist, function(index, tserialnumber){
                    var serialtr = $('<tr></tr>').html('<td>'+tserialnumber.serialnumber_content+'</td>');
                    serialtr.attr({
                        'class': 'aas-unpack', 'serialnumberid': tserialnumber.serialnumber_id,
                        'id': 'serialnumber_'+tserialnumber.serialnumber_id
                    });
                    $('#pass_list').append(serialtr);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }

    // 加载未打包序列号
    action_loading_unpacklist();


});
