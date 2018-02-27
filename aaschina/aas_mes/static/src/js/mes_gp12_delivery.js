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
                var temptr = $('#label_'+label.id);
                if (temptr!=undefined && temptr.length > 0){
                    layer.msg("标签已存在，请不要重复扫描！", {icon: 5});
                    return ;
                }
                var totalqty = parseFloat($('#mes_totalqty').attr('qty'));
                totalqty += label.product_qty;
                $('#mes_label').html(label.name);
                $('#mes_totalqty').attr('qty', totalqty).html(totalqty);
                var labeltr = $('<tr class="aaslabel"></tr>').prependTo($('#label_list'));
                labeltr.attr({'labelid': label.id, 'id': 'label_'+label.id});
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
        layer.confirm('您确认是返回检测操作？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
            window.location.replace('/aasmes/gp12/checking');
        },function(){});
    });

    //确认出货
    $('#action_dodelivery').click(function(){
        var labellist = $('.aaslabel');
        if(labellist.length <= 0){
            layer.msg('您还未添加出货明细，请先扫描需要出货条码！', {icon: 5});
            return;
        }
        var labelids = [];
        $.each(labellist, function(index, labeltr){
            labelids.push(parseInt($(labeltr).attr('labelid')));
        });
        layer.confirm('您确认提交出货？', {'btn': ['确定', '取消']}, function(index){
            layer.close(index);
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
