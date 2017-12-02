/**
 * Created by luforn on 2017-11-30.
 */

$(function(){

    var scanable = true;

    new VScanner(function(barcode){
        if(barcode==null || barcode==''){
            layer.msg('扫描条码异常！', {icon: 5});
            return ;
        }
        action_scanlabel(barcode);
    });


    function action_scanlabel(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var labelidstr = $('#delivery_todolist').attr('labelids');
        var labelids = [];
        if (labelidstr!='0' && labelidstr!='' && labelidstr!=null){
            labelids = labelidstr.split(',');
        }
        var scanparams = {'barcode': barcode, 'labelids': labelids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aaswms/delivery/scanlabel',
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
                if(labelidstr=='0'){
                    $('#delivery_todolist').html('').attr('labelids', dresult.label_id);
                }else{
                    $('#delivery_todolist').attr('labelids', labelidstr+','+dresult.label_id);
                }
                var producttr = $('#product'+dresult.product_id);
                var trcount = $('tr', $('#delivery_todolist')).length;
                if(producttr.length<=0){
                    producttr = $("<tr></tr>").appendTo($('#delivery_todolist'));
                    producttr.attr({
                        'id': 'product'+dresult.product_id,
                        'product_qty': dresult.product_qty,
                        'label_count': 1
                    })
                    $("<td></td>").html(trcount+1).appendTo(producttr);
                    $("<td></td>").html(dresult.product_code).appendTo(producttr);
                    $("<td></td>").html(dresult.product_qty).appendTo(producttr);
                    $("<td></td>").html('1').appendTo(producttr);
                }else{
                    var product_qty = parseFloat(producttr.attr('product_qty')) + dresult.product_qty;
                    var label_count = parseInt(producttr.attr('label_count')) + 1;
                    $('td:eq(2)', producttr).html(product_qty);
                    $('td:eq(3)', producttr).html(label_count);
                    producttr.attr({'product_qty': product_qty, 'label_count': label_count});
                }
                $('#mes_label').attr({'labelid': dresult.label_id, 'productid': dresult.product_id}).html(dresult.label_name);
                $('#mes_qty').attr('qty', dresult.product_qty).html(dresult.product_qty);
                var labelcount = parseInt($('#mes_count').attr('count'))+1;
                $('#mes_count').attr('count',labelcount).html(labelcount);
                $('#mes_productcode').html(dresult.product_code);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //清除当前扫描
    $('#delivery_clear_scan').click(function(){
        layer.confirm('您确认要清除最近一次扫描信息吗？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            action_clean_scan();
        }, function(){});
    });

    function action_clean_scan(){
        var labelid = $('#mes_label').attr('labelid');
        var productid = $('#mes_label').attr('productid');
        var qty = parseFloat($('#mes_qty').attr('qty'));
        if(labelid=='0'){
            return ;
        }
        var producttr = $('#product'+productid);
        if(producttr.length<=0){
            return ;
        }
        var labelidstr = $('#delivery_todolist').attr('labelids');
        if(labelidstr == '0'){
            return ;
        }
        var labelids = [];
        $.each(labelidstr.split(','), function(index, tid){
            if(tid != labelid){
                labelids.push(tid);
            }
        });
        var product_qty = parseFloat(producttr.attr('product_qty')) - qty;
        var label_count = parseInt(producttr.attr('label_count')) - 1;
        if(product_qty<=0.0 && label_count<=0){
            producttr.remove();
        }else {
            producttr.attr({'product_qty': product_qty, 'label_count': label_count});
            $('td:eq(2)', producttr).html(product_qty);
            $('td:eq(3)', producttr).html(label_count);
        }
        $('#mes_label').attr({'labelid': 0, 'productid': 0}).html('');
        $('#mes_qty').attr('qty', '0').html('');
        var tempcount = parseInt($('#mes_count').attr('count')) - 1;
        $('#mes_count').attr('count', tempcount).html(tempcount);
        $('#mes_productcode').html('');
        if(labelids.length==0){
            labelids = ['0'];
        }
        $('#delivery_todolist').attr('labelids', labelids.join(','));
    }

    //完成出库
    $('#delivery_done').click(function(){
        var labelidstr = $('#delivery_todolist').attr('labelids');
        if(labelidstr=='0' || labelidstr=='' || labelidstr==null){
            layer.msg('请先扫描出货标签！', {icon: 5});
            return ;
        }
        layer.confirm('您确认完成出货吗？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            var labelids = [];
            $.each(labelidstr.split(','), function(index, tid){
                labelids.push(parseInt(tid));
            });
            action_done(labelids);
        }, function(){});
    });

    function action_done(labelids){
        var params = {'labelids': labelids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aaswms/delivery/actiondone',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
            success:function(data){
                scanable = true;
                var dresult = data.result;
                if(!dresult.success){
                    layer.msg(dresult.message, {icon: 5});
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

});
