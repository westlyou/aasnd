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
            url: '/aasmes/repairing/scanserialnumber',
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
                $('#mes_serialnumber').html(dresult.serialnumber_name).attr('serialnumberid', dresult.serialnumber_id);
                $('#mes_customerpn').html(dresult.customerpn);
                $('#mes_internalpn').html(dresult.internalpn);
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
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    $('#action_repair').click(function(){
        var employeeid = parseInt($('#mes_employee').attr('employeeid'));
        if(employeeid==0){
            layer.msg('您还未添加维修人员，请先添加维修人员！', {icon: 5});
            return ;
        }
        var serialnumberid = parseInt($('#mes_serialnumber').attr('serialnumberid'));
        if(serialnumberid==0){
            layer.msg('您还未扫描成品条码，请先扫描成品条码！', {icon: 5});
            return ;
        }
        var repairesult = $('#mes_result').val();
        if(repairesult==null || repairesult==''){
           repairesult = 'ok';
        }
        var scanparams = {'serialnumberid': serialnumberid, 'repairerid': employeeid, 'repairesult': repairesult};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/repairing/actiondone',
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
                $('#mes_serialnumber').html('').attr('serialnumberid', '0');
                $('#mes_customerpn').html('');
                $('#mes_internalpn').html('');
                $('#rework_list').html('');
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    });

});