/**
 * Created by luforn on 2018-3-4.
 */

$(function(){

    function isAASFloat(val){
        var reg = /^(-?\d+)(\.\d+)?$/;
        if(reg.test(val)){
            return true;
        }
        return false;
    }

    new VScanner(function(barcode) {
        if (barcode == null || barcode == '') {
            layer.msg('扫描条码异常！', {icon: 5});
            return;
        }
        var prefix = barcode.substring(0,2);
        if(prefix=='AK'){
            action_scan_equipment(barcode);
        }else{
            action_scan_employee(barcode);
        }
    });

    function action_scan_equipment(barcode){
        var temparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/producttest/scanequipment',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_equipment').attr('equipmentid', dresult.equipment_id).html(dresult.equipment_code);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    function action_scan_employee(barcode){
        var temparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/producttest/scanemployee',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_employee').attr('employeeid', dresult.employee_id).html(dresult.employee_name);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    $('#mes_workstation').select2({
        placeholder: '选择产线工位...',
        ajax:{
            type: 'post',
            timeout:10000,
            dataType: 'json',
            url: '/aasmes/producttest/loadworkstations',
            headers:{'Content-Type':'application/json'},
            data: function(params){
                var meslineid = parseInt($('#mes_mesline').attr('meslineid'));
                var sparams =  {'q': params.term || '', 'page': params.page || 1, 'meslineid': meslineid};
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

    $("#mes_workstation").on("select2:select",function(){
        var tempval = $(this).val();
        if (tempval==null || tempval=='0'){
            return ;
        }
        var workstationid = parseInt(tempval);
        var testtype = $('#action_commit').attr('testtype');
        var productid = parseInt($('#mes_product').attr('productid'));
        if(productid==0 || workstationid==0){
            return ;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var temparams = {'productid': productid, 'workstationid': workstationid, 'testtype': testtype};
        $.ajax({
            url: '/aasmes/producttest/loadparameters',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.parameters.length <= 0){
                    return ;
                }
                var parameterlist = $('#parameterlist');
                parameterlist.html('');
                $.each(dresult.parameters, function(index, param){
                    var temptr = $('<tr></tr>').appendTo(parameterlist);
                    $('<td></td>').html('<span>'+param.name+'</span>').appendTo(temptr);
                    $('<td></td>').html('<span>'+param.type+'</span>').appendTo(temptr);
                    var pvalstr = '<div class="form-group"> ' +
                            '<div class="col-sm-12" pid="'+param.id+'" pname="'+param.name+'" ptype="'+param.type+'">' +
                                '<input type="text" class="form-control aas-parameter"/>' +
                            '</div> ' +
                        '</div>';
                    $('<td></td>').html(pvalstr).appendTo(temptr);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    });

    //提交检测值
    $('#action_commit').click(function(){
        var workstationid = $('#mes_workstation').val();
        if(workstationid==null || workstationid==0){
            layer.msg('请先设置好工位！', {icon: 5});
            return ;
        }
        var equipmentid = parseInt($('#mes_equipment').attr('equipmentid'));
        var employeeid = parseInt($('#mes_employee').attr('employeeid'));
        if(employeeid=='0'){
            layer.msg('员工异常，请先扫描员工再继续其他操作！', {icon: 5});
            return ;
        }
        var workorderid = $('#mes_workorder').attr('workorderid');
        if(workorderid==undefined || workorderid==null || workorderid=='0'){
            layer.msg('工单异常，当前产线可能还未制定即将生产的工单！', {icon: 5});
            return ;
        }
        var parameterlist = $('input.aas-parameter');
        if(parameterlist==undefined || parameterlist.length<=0){
            layer.msg('检测参数异常，请先检查是否设置了检测参数！', {icon: 5});
            return ;
        }
        var paramlist = [];
        var messagelist = [];
        $.each(parameterlist, function(index, tempipt){
            var pflag = true;
            var tempval = $(tempipt).val();
            var parentdiv = $(tempipt).parent();
            var pid = parseInt(parentdiv.attr('pid'));
            var pname = parentdiv.attr('pname');
            var ptype = parentdiv.attr('ptype');
            if(tempval==null || tempval==''){
                pflag = false;
                messagelist.push('参数：'+pname+'还未设置检测值');
            }
            if(ptype=='number' && !isAASFloat(tempval)){
                pflag = false;
                messagelist.push('参数：'+pname+'检测值不是一个有效数值');
            }
            var superdiv = parentdiv.parent();
            if(pflag){
                if(superdiv.hasClass('has-error')){
                    superdiv.removeClass('has-error');
                }
                paramlist.push({'parameter_id': pid, 'parameter_value': tempval});
            }else if(!superdiv.hasClass('has-error')){
                superdiv.addClass('has-error');
            }
        });
        if(messagelist.length > 0){
            layer.msg(messagelist.join(';'), {icon: 5});
            return ;
        }
        if(paramlist.length <= 0){
            layer.msg('检测参数异常，当前未获取到有效的检测参数信息！', {icon: 5});
            return ;
        }
        var testtype = $('#action_commit').attr('testtype');
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var testparams = {
            'testtype': testtype, 'workstationid': parseInt(workstationid),
            'workorderid': parseInt(workorderid), 'employeeid': employeeid, 'parameters': paramlist
        };
        if(equipmentid > 0){
            testparams['equipmentid'] = equipmentid
        }
        $.ajax({
            url: '/aasmes/producttest/docommittest',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: testparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                window.location.replace('/aasmes/producttest/orderdetail/'+dresult.orderid);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });

    });

});
