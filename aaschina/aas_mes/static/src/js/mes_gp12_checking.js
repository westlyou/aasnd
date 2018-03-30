/**
 * Created by luforn on 2017-10-19.
 */

$(function() {
    //初始化语音播报参数
    var speechmsg = new SpeechSynthesisUtterance();
    speechmsg.lang = 'zh';
    speechmsg.rate = 1.3;

    function myspeak(msg){
        speechmsg.text = msg;
        speechSynthesis.speak(speechmsg);
    }


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
                if(dresult.action=='leave'){
                    var currentemployeeid = $('#mes_scanner').attr('employeeid');
                    if (currentemployeeid==dresult.employee_id){
                        $('#mes_scanner').attr('employeeid', '0').html('');
                    }else{
                        $('#checker_'+dresult.employee_id).remove();
                    }
                    action_leave(dresult.attendance_id);
                    return ;
                }
                var temployee = {
                    'employee_id': dresult.employee_id,
                    'employee_name': dresult.employee_name, 'employee_code': dresult.employee_code
                };
                if(dresult.needrole){
                    // layer.msg(dresult.message, {icon: 1});
                    initcheckingrolehtml(temployee);
                }else{
                    changeemployeerole(temployee, 'check');
                }
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    function initcheckingrolehtml(employee){
        var tcontent = '<div class="row" style="margin-top: 10px;clear: both;zoom: 1; padding:0px 20px;">';

        tcontent += '<div class="col-md-6">';
        tcontent += '<a href="javascript:void(0);" class="btn btn-block btn-success aas-action" ';
        tcontent += 'style="margin-top:10px;margin-bottom:10px; height:100px; line-height:100px; font-size:25px; padding:0;" ';
        tcontent += 'actiontype="scan">扫描</a>';
        tcontent += '</div>';

        tcontent += '<div class="col-md-6">';
        tcontent += '<a href="javascript:void(0);" class="btn btn-block btn-success aas-action" ';
        tcontent += 'style="margin-top:10px;margin-bottom:10px; height:100px; line-height:100px; font-size:25px; padding:0;" ';
        tcontent += 'actiontype="check">目检</a>';
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
            layer.close(lindex);
            var self = $(this);
            changeemployeerole(employee, self.attr('actiontype'));
        });
    }

    function changeemployeerole(temployee, role){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var tparams = {'employeeid': temployee.employee_id, 'action_type': role};
        $.ajax({
            url: '/aasmes/gp12/changemployeerole',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: tparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(role=='scan'){
                    $('#mes_scanner').attr('employeeid', temployee.employee_id).html(temployee.employee_name);
                }else if(role=='check'){
                    var templi = $('<li></li>').attr('id', 'checker_'+temployee.employee_id);
                    templi.appendTo($('#checker_list'));
                    templi.html('<a href="javascript:void(0);">'+temployee.employee_name+
                        '<span class="pull-right">'+temployee.employee_code+'</span></a>');
                }
                layer.msg('您已上岗，祝您工作愉快！', {icon: 1});
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
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
        var employeeid = parseInt($('#mes_scanner').attr('employeeid'));
        if(employeeid==0){
            scanable = true;
            layer.msg('请先设置扫描员工！', {icon: 5});
            return ;
        }
        var labelqty = $('#mes_labelqty').val();
        if(!isAboveZeroInteger(labelqty)){
            layer.msg('请先设置好数量信息！', {icon: 5});
            return ;
        }
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var productid = parseInt($('#mes_currentpn').attr('productid'));
        if(productid!=0){
            scanparams['productid'] = productid;
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
                $('#mes_serialnumber').html(barcode);
                $('#check_result').html(dresult.result);
                if(dresult.done){
                    $('#gp12_result_content').html($('#gp12_result_content').attr('serialcount'));
                    myspeak('已扫描，请不要重复操作');
                    return ;
                }
                if(dresult.result=='OK'){
                    $('#gp12_result_box').removeClass('bg-red').addClass('bg-green');
                    var serialnumbertr = $('#serialnumber_'+dresult.serialnumber_id);
                    if(serialnumbertr.length > 0){
                        serialnumbertr.remove();
                    }else{
                        var scount = parseInt($('#gp12_result_content').attr('serialcount'));
                        scount += 1;
                        $('#gp12_result_content').attr('serialcount', scount).html(scount);
                        var waitcount = parseInt($('#mes_printbtn').attr('waitcount'));
                        $('#mes_printbtn').attr('waitcount', waitcount+1);
                        myspeak($('#gp12_result_content').html());
                    }
                    var serialtr = $('<tr></tr>').prependTo($('#pass_list')).html('<td>'+dresult.operate_result+'</td>');
                    serialtr.attr({
                        'class': 'aas-unpack',
                        'serialnumberid': dresult.serialnumber_id, 'id': 'serialnumber_'+dresult.serialnumber_id
                    });
                }else{
                    $('#gp12_result_box').removeClass('bg-green').addClass('bg-red');
                    $('#fail_list').append('<tr><td>'+dresult.operate_result+'</td></tr>');
                    $('#gp12_result_content').html('N G');
                    myspeak('N G');
                }
                if(dresult.message!=null && dresult.message!=''){
                    $('#checkwarning').html(dresult.message);
                }
                var custmoercodespan = $('#mes_currentpn');
                var productid = parseInt(custmoercodespan.attr('productid'));
                if(productid==0){
                    custmoercodespan.attr('productid', dresult.productid).html(dresult.productcode);
                }else if(productid != dresult.productid){
                    layer.msg('条码异常可能混入其他型号产品，请仔细检查！', {icon: 5});
                    return ;
                }
                var waitcount = parseInt($('#mes_printbtn').attr('waitcount'));
                var labelqty = parseInt($('#mes_labelqty').val());
                if(waitcount >= labelqty){
                    action_print_label(labelqty);
                }else{
                    action_show_operationandreworklist(dresult.serialnumber_id);
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
        action_show_operationandreworklist(serialnumberid);
    });

    function action_show_operationandreworklist(serialnumberid){
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
                $('#operation_list').html('');
                if(dresult.operationlist.length > 0){
                    $.each(dresult.operationlist, function(index, record){
                        var lineno = index+1;
                        var operationtr = $('<tr></tr>').appendTo($('#operation_list'));
                        $('<td></td>').html(lineno).appendTo(operationtr);
                        $('<td></td>').html(record.operation_name).appendTo(operationtr);
                        $('<td></td>').html(record.operate_time).appendTo(operationtr);
                        $('<td></td>').html(record.operate_result).appendTo(operationtr);
                        $('<td></td>').html(record.scanner_name).appendTo(operationtr);
                        $('<td></td>').html(record.checker_name).appendTo(operationtr);
                        $('<td></td>').html(record.operator_name).appendTo(operationtr);
                        $('<td></td>').html(record.operate_equipment).appendTo(operationtr);
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
    }

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
                myspeak('标签已经打印，请注意查收');
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
        var labelqty = $('#mes_labelqty').val();
        if(!isAboveZeroInteger(labelqty)){
            layer.msg('请先设置有效的数量信息', {icon: 5});
            return ;
        }
        labelqty = parseInt(labelqty);
        var tipmessage = '您确认要打印标签吗？';
        if(waitcount < labelqty){
            tipmessage = '当前成品数量少于'+labelqty+',您确认要打印标签吗？';
        }
        layer.confirm(tipmessage, {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            action_print_label(waitcount);
        },function(){});
    });

    //上报不良
    $('#action_badmode').click(function(){
        layer.confirm('您确认上报不良？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            var gp12scanner = $('#mes_scanner');
            var scannerid = gp12scanner.attr('employeeid');
            if(scannerid==null || scannerid=='0' || scannerid==''){
                layer.msg('当前扫描员工还没上岗，请扫描员工先上岗再操作！', {icon: 5});
                return ;
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
                var sparams =  {'q': params.term || '', 'page': params.page || 1};
                return JSON.stringify({
                    jsonrpc: "2.0", method: 'call', params: sparams, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
                });
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

    function gettoday(){
        var tempdate = new Date();
        var tyear = tempdate.getFullYear();
        var tmonth = tempdate.getMonth() + 1;
        var tdate = tempdate.getDate();
        if(tmonth>=1 && tmonth<=9){
            tmonth = "0" + tmonth;
        }
        if(tdate>=1 && tdate<=9){
            tdate = "0"+tdate;
        }
        return tyear+'-'+tmonth+'-'+tdate;
    }

    $('#checkdate').val(gettoday());

    $('#checkdate').datepicker({clearBtn: true, autoclose: true, language: 'zh-CN', format: 'yyyy-mm-dd'});

    $('#changedatebtn').click(function(){
        var checkdate = $('#checkdate').val();
        if(checkdate==undefined || checkdate==null || checkdate==''){
            checkdate = gettoday();
        }
        action_loading_unpacklist(checkdate);
    });

    function action_loading_unpacklist(checkdate){
        if(checkdate==undefined || checkdate==null){
            checkdate = gettoday();
        }
        var temparams = {'checkdate': checkdate};
        $.ajax({
            url: '/aasmes/gp12/loadunpacklist',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:30000, dataType: 'json',
            data: JSON.stringify({
                jsonrpc: "2.0", method: 'call', params: temparams,
                id: Math.floor(Math.random() * 1000 * 1000 * 1000)
            }),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_currentpn').attr('productid', dresult.productid).html(dresult.productcode);
                $('#mes_serialnumber').html(dresult.serialnumber);
                $('#gp12_result_content').attr('serialcount', dresult.serialcount).html(dresult.serialcount);
                $('#pass_list').html('');
                $('#mes_printbtn').attr('waitcount', dresult.serialcount);
                $('#operation_list').html('');
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

    $('#mes_printer').on('select2:select', function(event){
        var selectedatas = $('#mes_printer').select2('data');
        var printerobj = selectedatas[0];
        var cdate = new Date();
        var cyear = cdate.getFullYear();
        var cmonth = cdate.getMonth()+1;
        var cday = cdate.getDate();
        var currentdate = cyear+'-'+cmonth+'-'+cday;
        localStorage.setItem('check_date', currentdate);
        localStorage.setItem('printer_id', printerobj.id);
        localStorage.setItem('printer_name', printerobj.text);
    });

    function setdefault_printer(){
        var printer_id = localStorage.getItem('printer_id');
        var printer_name = localStorage.getItem('printer_name');
        var check_date = localStorage.getItem('check_date');
        if(printer_id==null || printer_name==null || check_date==null){
            return ;
        }
        var cdate = new Date();
        var cyear = cdate.getFullYear();
        var cmonth = cdate.getMonth()+1;
        var cday = cdate.getDate();
        var currentdate = cyear+'-'+cmonth+'-'+cday;
        if(check_date!=currentdate){
            return ;
        }
        $('#mes_printer').val(printer_id);
        $('#mes_printer').html("<option value="+printer_id+">"+printer_name+"</option>");
    }
    //设置默认打印机
    setdefault_printer();

    function setdefault_labelqty(){
        var label_qty = localStorage.getItem('label_qty');
        var check_date = localStorage.getItem('check_date');
        if(label_qty==null || check_date==null){
            return ;
        }
        var cdate = new Date();
        var cyear = cdate.getFullYear();
        var cmonth = cdate.getMonth()+1;
        var cday = cdate.getDate();
        var currentdate = cyear+'-'+cmonth+'-'+cday;
        if(check_date!=currentdate){
            return ;
        }
        $('#mes_labelqty').val(label_qty);
    }

    //设置默认标签数量
    setdefault_labelqty();

    $('li.aas-qty').click(function(){
        var tempqty = $(this).attr('qty');
        $('#mes_labelqty').val(tempqty);
        $('#mes_labelqty').attr('readonly', 'readonly');
        var cdate = new Date();
        var cyear = cdate.getFullYear();
        var cmonth = cdate.getMonth()+1;
        var cday = cdate.getDate();
        var currentdate = cyear+'-'+cmonth+'-'+cday;
        localStorage.setItem('check_date', currentdate);
        localStorage.setItem('label_qty', tempqty);
    });

    $('#other_qty').click(function(){
        $('#mes_labelqty').removeAttr('readonly').val('');
    });

    function isAboveZeroInteger(val){
        var reg = /^[1-9]\d*$/;
        if(reg.test(val)){ return true; }
        return false;
    }

    $('#mes_labelqty').change(function(){
        var labelqty = $(this).val();
        if(!isAboveZeroInteger(labelqty)){
            layer.msg('请设置有效的数量！例如：90、180', {icon: 5});
            return ;
        }
        var cdate = new Date();
        var cyear = cdate.getFullYear();
        var cmonth = cdate.getMonth()+1;
        var cday = cdate.getDate();
        var currentdate = cyear+'-'+cmonth+'-'+cday;
        localStorage.setItem('check_date', currentdate);
        localStorage.setItem('label_qty', labelqty);
    });


});
