/**
 * Created by luforn on 2018-6-4.
 */

$(function(){

    //初始化默认员工
    var repairerstr = localStorage.getItem('repairer');
    if(repairerstr!=null && repairerstr!=''){
        var repairer = JSON.parse(repairerstr);
        $('#mes_repairer').attr('employeeid', repairer.employee_id).val(repairer.employee_name);
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


    function action_scan_employee(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/repairing/scanemployee',
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
                var empdata = {'employee_id': dresult.employee_id, 'employee_name': dresult.employee_name};
                localStorage.setItem('repairer', JSON.stringify(empdata));
                $('#mes_repairer').attr('employeeid', dresult.employee_id).val(dresult.employee_name);
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
            url: '/aasmes/repairing/start/scanserialnumber',
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
                var temprework = $('#rework_'+dresult.rework_id);
                if(temprework!=undefined && temprework!=null && temprework.length>0){
                    layer.msg('已扫描，请不要重复操作！', {icon: 5});
                    return ;
                }
                $('#mes_serialnumber').val(dresult.serialnumber_name);
                $('#mes_productcode').val(dresult.productcode);
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
                    });
                }
                var templi = $('<li class="aas-serialnumber"></li>').attr({
                    'reworkid': dresult.rework_id, 'id': 'rework_'+dresult.rework_id
                }).prependTo($('#serialnumberlist'));
                var tempa = $('<a href="javascript:void(0);"></a>').appendTo(templi).append(dresult.serialnumber_name);
                $('<span class="label label-danger pull-right">删除</span>').appendTo(tempa).attr({
                    'reworkid': dresult.rework_id
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
        var self = $(this);
        var templi = $('#rework_'+self.attr('reworkid'));
        if(templi!=undefined && templi.length>0){
            templi.remove();
        }
    });

    $('#action_repair_back').click(function(){
        layer.confirm('您确认要返回维修主页面吗？', {'btn': ['确认', '取消']}, function(index) {
            layer.close(index);
            window.location.replace('/aasmes/repairing');
        });
    });

    $('#action_repair_dostart').click(function(){
        layer.confirm('您确认要提交扫描记录吗？', {'btn': ['确认', '取消']}, function(index) {
            layer.close(index);
            action_dostart();
        });
    });

    function action_dostart(){
        var repairerid = parseInt($('#mes_repairer').attr('employeeid'));
        if(repairerid==0){
            layer.msg('请先扫描维修员工！', {icon: 5});
            return ;
        }
        var serialnumberlist = $('.aas-serialnumber');
        if(serialnumberlist==undefined || serialnumberlist==null || serialnumberlist.length<=0){
            layer.msg('请先扫描需要维修的序列号！', {icon: 5});
            return ;
        }
        var reworkids = [];
        $.each(serialnumberlist, function(index, rework){
            reworkids.push(parseInt($(rework).attr('reworkid')));
        });
        var temparams = {'repairerid': repairerid, 'reworkids': reworkids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/repairing/start/done',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                window.location.replace('/aasmes/repairing');
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
            }
        });

    }

    //清理员工
    $('#clearrepairer').click(function(){
        $('#mes_repairer').attr('employeeid', '0').val('');
        localStorage.setItem('repairer', '');
    });

});
