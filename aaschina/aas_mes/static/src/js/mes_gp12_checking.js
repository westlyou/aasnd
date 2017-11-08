/**
 * Created by luforn on 2017-10-19.
 */

$(function() {

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
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#check_result').html(dresult.result);
                if(dresult.result=='OK'){
                    $('#check_result_box').removeClass('bg-red').addClass('bg-green');
                    $('#pass_list').append('<tr><td>'+dresult.operate_result+'</td></tr>');
                    var scount = parseInt($('#pass_count').attr('scount'));
                    scount += 1;
                    $('#pass_count').attr('scount', scount).html(scount);
                }else{
                    $('#check_result_box').removeClass('bg-green').addClass('bg-red');
                    $('#fail_list').append('<tr><td>'+dresult.operate_result+'</td></tr>');
                }
                if(dresult.message!=null && dresult.message!=''){
                    $('#checkwarning').html(dresult.message);
                }
                var custmoercodespan = $('#mes_currentpn');
                var customercode = custmoercodespan.attr('customercode');
                if(customercode==null || customercode==''){
                    custmoercodespan.attr('customercode', dresult.productcode).html(dresult.productcode);
                }
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
                $('#mes_serialnumber').html(barcode);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //单击员工清单
    $('#employee_list').on('click', '.aas-employee', function(){
        var self = $(this);
        var employeeid = self.attr('employeeid');
        var employeename = self.attr('employeename');
        $('#mes_operator').attr('employeeid', employeeid).html(employeename);
    });

});
