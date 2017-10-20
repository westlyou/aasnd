/**
 * Created by luforn on 2017-10-19.
 */

$(function() {

    var scanable = true; //是否可以继续扫描
    new VScanner(function(barcode) {
        if (barcode == null || barcode == '') {
            layer.msg('扫描条码异常！', {icon: 5});
            return;
        }
        var prefix = barcode.substring(0,2);
        if(prefix=='AM'){
            action_scan_employee();
        }else{
            action_scan_serialnumber();
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
                    var currentemployeeid = $('#current_employee').attr('employeeid');
                    if (currentemployeeid==dresult.employee_id){
                        $('#current_employee').attr('employeeid', '0').html('');
                    }
                    $('#employee_'+dresult.employee_id).remove();
                    return ;
                }
                var employeeli = $('<li class="aas-employee"></li>').appendTo($('#menulist'));
                employeeli.attr('id', 'employee_'+dresult.employee_id);
                employeeli.html('<a href="javascript:void(0);" style="font-size:25px;font-weight:bold;"><span>'+dresult.employee_name+'</span></a>');
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
        scanable = false;
        var employeeid = parseInt($('#current_employee').attr('employeeid'));
        if(employeeid==0){
            layer.msg('请在左侧员工列表中选择一个当前操作员工', {icon: 5});
            return ;
        }
        var scanparams = {'barcode': barcode, 'employeeid': employeeid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var customercode = $('#customer_code').attr('customercode');
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
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                var checkresult = $('#check_result');
                if(dresult.result=='OK'){
                    checkresult.css({'color': 'green'}).html(dresult.result);
                }else{
                    checkresult.css({'color': 'red'}).html(dresult.result);
                }
                if(dresult.message!=null && dresult.message!=''){
                    $('#checking_message').html(dresult.message);
                }
                var custmoercodespan = $('#customer_code');
                var customercode = custmoercodespan.attr('customercode');
                if(customercode==null || customercode==''){
                    custmoercodespan.attr('customercode', dresult.productcode);
                }
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

});
