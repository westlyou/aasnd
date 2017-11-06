/**
 * Created by luforn on 2017-11-3.
 */

$(function(){

    function isAboveZeroFloat(val){
        var reg = /^(\d+)(\.\d+)?$/;
        if (reg.test(val)){ return true; }
        return false;
    }

    new VScanner(function(barcode){
        if(barcode==null || barcode==''){
            layer.msg('扫描条码异常！', {icon: 5});
            return ;
        }
        var prefix = barcode.substring(0,2);
        if(prefix=='AM'){
            action_scanemployee(barcode);
        }else if(prefix=='AU'){
            action_scanwireorder(barcode);
        }else if(prefix=='AT'){
            action_scancontainer(barcode);
        }else{
            layer.msg('扫描异常，请确认是否在扫描员工工牌或线材工单！', {icon: 5});
            return ;
        }
    });

    //扫描员工卡
    function action_scanemployee(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scanemployee',
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
                    $('#wirecut_employees').append(templi);
                }else{
                    var templi = $('#employee_'+dresult.employee_id);
                    templi.remove();
                }
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //扫描线材工单
    function action_scanwireorder(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scanwireorder',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success:function(data){
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                if(dresult.wireorder_id == $('#mes_wireorder').attr('wireorderid')){
                    layer.msg('线材工单已经扫描过，请不要重复操作！', {icon: 5});
                    return ;
                }
                $('#mes_wireorder').attr('wireorderid', dresult.wireorder_id);
                $('#mes_wireorder').html(dresult.wireorder_name);
                $('#mes_product').html(dresult.product_code);
                $('#mes_pqty').html(dresult.product_qty);
                $('#workorderlist').html('');
                $.each(dresult.workorderlist, function(workorder){
                    var workorder_id = 'workorder_'+workorder.id;
                    var ordertr = $('<tr></tr>').attr({
                        'id': workorder_id, 'output_qty': workorder.output_qty,
                        'workorderid': workorder.id, 'order_name': workorder.order_name, 'product_code': workorder.product_code
                    });
                    $('<td></td>').appendTo(ordertr).html('<input class="ordercheck" wid="'+workorder_id+'" type="checkbox"/>');
                    $('<td></td>').appendTo(ordertr).html(workorder.order_name);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_code);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_uom);
                    $('<td></td>').appendTo(ordertr).html(workorder.product_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.output_qty);
                    $('<td></td>').appendTo(ordertr).html(workorder.state_name);
                    $('#workorderlist').append(ordertr);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //扫描容器
    function action_scancontainer(barcode){
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/wirecutting/scancontainer',
            headers: {'Content-Type': 'application/json'},
            type: 'post', timeout: 10000, dataType: 'json',
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: scanparams, id: access_id}),
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                $('#mes_container').attr('containerid', dresult.container_id).html(dresult.container_name);
            },
            error:function(xhr,type,errorThrown){ console.log(type);}
        });
    }

    //产出
    $('#wire_output').click(function(){
        var self = this;
        var wireorderid = parseInt($('#mes_wireorder').attr('wireorderid'));
        if(wireorderid==0){
            layer.msg('您还未扫描线材工单！', {icon: 5});
            return ;
        }
        var workorderid = parseInt($('#mes_workorder').attr('workorderid'));
        if (workorderid==0){
            layer.msg('您还没选择需要产出的线材，请先选择需要产出的线材！', {icon: 5});
            return ;
        }
        var containerid = parseInt($('#mes_container').attr('containerid'));
        if(containerid==0){
            layer.msg('您还没添加产出容器，请先扫描容器标签添加容器！', {icon: 5});
            return ;
        }
        layer.prompt({title: '输入需要产出数量，并确认', formType: 3}, function(text, index){
            if(!isAboveZeroFloat(text)){
                layer.msg('产出数量必须是一个大于零的整数！', {icon: 5});
                return ;
            }
            layer.close(index);
            var output_qty = parseFloat(text);
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var outputparams = {'workorder_id': workorderid, 'output_qty': output_qty, 'container_id': containerid};
            $.ajax({
                url: '/aasmes/wirecutting/output',
                headers:{'Content-Type':'application/json'},
                type: 'post', timeout:10000, dataType: 'json',
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: outputparams, id: access_id}),
                success:function(data){
                    var dresult = data.result;
                    if(!dresult.success){
                        layer.msg(dresult.message, {icon: 5});
                        return ;
                    }
                    $('#workorder_'+workorderid).children().eq(5).html(dresult.output_qty);
                    $('#workorder_'+workorderid).children().eq(6).html(dresult.state_name);
                },
                error:function(xhr,type,errorThrown){ console.log(type);}
            });
        });
    });


    //切换生产子工单
    $('.ordercheck').change(function(){
        var wid = $(this).attr('wid');
        $.each($('.ordercheck'), function(){
            var twid = $(this).attr('wid');
            if(twid!=wid){
                $(this).attr('checked',false);
            }
        });
        var workordertr = $('#'+wid);
        if($(this).attr('checked')){
            $('#mes_workorder').attr('workorderid', workordertr.attr('workorderid'));
            $('#mes_workorder').html(workordertr.attr('order_name'));
        }else{
            $('#mes_workorder').attr('workorderid', '0');
            $('#mes_workorder').html('');
        }
    });

});
