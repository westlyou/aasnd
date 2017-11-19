/**
 * Created by luforn on 2017-11-19.
 */

$(function(){

    var scanable = true; //是否可以继续扫描
    new VScanner(function(barcode) {
        if (barcode == null || barcode == '') {
            scanable = true;
            layer.msg('扫描条码异常！', {icon: 5});
            return;
        }
        action_scan_label(barcode);
    });

    function action_scan_label(barcode){
        if(!scanable){
            layer.msg('操作正在处理，请耐心等待！', {icon: 5});
            return ;
        }
        scanable = false;
        var scanparams = {'barcode': barcode};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/gp12/delivery/scanlabel',
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
                var label = dresult.label;
                var totalqty = parseFloat($('#mes_totalqty').attr('qty'));
                totalqty += label.product_qty;
                $('#mes_label').html(label.name);
                $('#mes_totalqty').attr('qty', totalqty).html(totalqty);
                var labeltr = $('<tr></tr>').prependTo($('#label_list')).attr('labelid', label.id);
                $('<td></td>').html(label.name).appendTo(labeltr);
                $('<td></td>').html(label.customerpn).appendTo(labeltr);
                $('<td></td>').html(label.internalpn).appendTo(labeltr);
                $('<td></td>').html(label.product_lot).appendTo(labeltr);
                $('<td></td>').html(label.product_qty).appendTo(labeltr);
            },
            error:function(xhr,type,errorThrown){
                scanable = true;
                console.log(type);
            }
        });
    }

    //返回检测
    $('#action_back_checking').click(function(){
        layer.confirm('您确认是返回检测操作？', {'btn': ['确定', '取消']}, function(){
            window.location.replace('/aasmes/gp12/checking');
        },function(){});
    });

    //确认出货
    $('#action_dodelivery').click(function(){
        var labellist = $('tr', '#label_list');
        if(labellist.length <= 0){
            layer.msg('您还未添加出货明细，请先扫描需要出货条码！', {icon: 5});
            return;
        }
        var labelids = [];
        $(labellist, function(index, labeltr){
            labelids.append(parseInt($(labeltr).attr('labelid')));
        });
        layer.confirm('您确认提交出货？', {'btn': ['确定', '取消']}, function(){
            action_delivery(labelids);
        },function(){});
    });

    function action_delivery(labelids){
        if(labelids==undefined || labelids.length <= 0){
            layer.msg('您还未添加出货明细，请先扫描需要出货条码！', {icon: 5});
            return;
        }
        var dparams = {'labelids': labelids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        $.ajax({
            url: '/aasmes/gp12/delivery/actiondone',
            headers:{'Content-Type':'application/json'},
            type: 'post', timeout:10000, dataType: 'json',
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: dparams, id: access_id}),
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
