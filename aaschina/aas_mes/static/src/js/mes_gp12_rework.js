/**
 * Created by luforn on 2017-11-16.
 */

$(function() {

    var employeeid = localStorage.getItem('employeeid');
    var employeename = localStorage.getItem('employeename');
    if(employeeid!=undefined&&employeeid!=null&&employeeid!=0){
        $('#mes_employee').attr('employeeid', employeeid);
    }
    if(employeename!=undefined&&employeename!=null&&employeename!=''){
        $('#mes_employee').val(employeename);
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
                if(dresult.message!=null && dresult.message!=''){
                    layer.msg(dresult.message, {icon: 1});
                }
                if(dresult.action=='leave'){
                    return ;
                }
                $('#mes_employee').attr('employeeid', dresult.employee_id);
                $('#mes_employee').val(dresult.employee_name);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }


});
